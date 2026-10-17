"""Release checks that never print secrets or equate configuration with live access."""
import argparse
import compileall
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    checks = {}
    checks["python_syntax"] = compileall.compile_dir(str(ROOT / "farmsync"), quiet=1)
    checks["direct_dependencies_pinned"] = all(re.fullmatch(r"[\w.-]+==[^\s]+", line.strip()) for line in (ROOT / "requirements.lock.txt").read_text().splitlines() if line.strip() and not line.startswith("#"))
    checks["aws_deployment_assets_exist"] = all((ROOT / p).is_file() for p in ["aws/worker_entry.py", "aws/api-requirements.txt", "requirements.aws.txt", "scripts/build_aws.py", "scripts/deploy_aws.py", "farmsync/cloud/api.py", "farmsync/cloud/store.py"])
    if not args.source_only:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        from farmsync.storage import Store
        store = Store()
        with store.connect() as db:
            checks["database_integrity"] = db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        checks["cadastral_dataset"] = (ROOT / "data/FAI_Product_Challange/TASK_2/Geospatial_Layer/Park_Cadastral_Map.geojson").is_file()
        checks["trained_crop_head"] = (ROOT / "farmsync/vision/weights/crop_model.pth").is_file()
        if args.production:
            origins = os.getenv("FARMSYNC_ALLOWED_ORIGINS", "").split(",")
            checks["production_mode"] = os.getenv("FARMSYNC_ENV") == "production"
            checks["individual_users"] = store.user_count() > 0
            checks["explicit_https_origins"] = all(o.strip().startswith("https://") and "example" not in o for o in origins)
            checks["browser_credentials_disabled"] = os.getenv("FARMSYNC_ALLOW_RUNTIME_CREDENTIALS", "false").lower() != "true"
            checks["ocr_artifacts"] = any(Path(os.getenv("FARMSYNC_OCR_MODEL_DIR", ".runtime/models/easyocr")).glob("*.pth"))
    output = {"checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()}, "all_passed": all(checks.values()),
              "scope": "Local preflight only. Live AWS, deployed HTTPS, restore and load acceptance are separate checks."}
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["all_passed"] else 1)


if __name__ == "__main__":
    main()
