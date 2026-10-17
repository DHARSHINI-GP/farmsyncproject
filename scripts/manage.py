"""Local operator commands; passwords are read interactively, never as CLI arguments."""
import argparse
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from farmsync.storage import Store
from farmsync.operations import backup, restore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=None)
    parser.add_argument('--cloud', action='store_true', help='Use the organizer DynamoDB/S3 deployment instead of local SQLite')
    sub = parser.add_subparsers(dest="command", required=True)
    user = sub.add_parser("create-user")
    user.add_argument("username")
    user.add_argument("--role", choices=["admin", "reviewer", "user"], default="user")
    disable = sub.add_parser("disable-user")
    disable.add_argument("username")
    save = sub.add_parser("backup")
    save.add_argument("destination")
    recover = sub.add_parser("restore")
    recover.add_argument("source")
    recover.add_argument("destination")
    args = parser.parse_args()
    if args.command == "restore":
        result = restore(args.source, args.destination)
        print("Restore integrity checks passed. New database:", result.path)
        return
    if args.cloud:
        import os
        from farmsync.cloud.store import CloudStore
        state_path=Path(__file__).resolve().parents[1]/'.runtime/aws-build/deployment-state.json'
        import json
        state=json.loads(state_path.read_text())
        os.environ.update(FARMSYNC_TABLE=state['table'],FARMSYNC_BUCKET=state['bucket'])
        store=CloudStore()
        if args.command not in {'create-user','disable-user'}:
            raise SystemExit('Cloud backups use DynamoDB PITR and versioned S3; see AWS_DEPLOYMENT.md')
    else:
        store = Store(args.database)
    if args.command == "create-user":
        password = getpass("Password (at least 12 characters): ")
        if password != getpass("Confirm password: "):
            raise SystemExit("Passwords did not match; no user created")
        result = store.create_user(args.username, password, args.role)
        print("Created", result["username"], "with role", result["role"])
    elif args.command == "disable-user":
        if args.cloud:
            name=store.get('NAME#'+args.username.casefold())
            if not name: raise SystemExit('User not found')
            store.table.update_item(Key={'PK':'USER#'+name['user_id'],'SK':'META'},UpdateExpression='SET disabled=:yes',ExpressionAttributeValues={':yes':True})
            print('User disabled; existing sessions will be rejected immediately')
            return
        with store.connect() as db:
            row = db.execute("SELECT id FROM users WHERE username=?", (args.username.casefold(),)).fetchone()
            if not row:
                raise SystemExit("User not found")
            db.execute("UPDATE users SET disabled=1 WHERE id=?", (row[0],))
            db.execute("DELETE FROM sessions WHERE user_id=?", (row[0],))
        print("User disabled and sessions revoked")
    else:
        print("Backup completed and checksummed:", backup(store, args.destination))


if __name__ == "__main__":
    main()
