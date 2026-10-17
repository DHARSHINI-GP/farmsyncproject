"""Small live checks of only organizer-approved Task 1 Bedrock models.

Creates no resources; model calls can incur a small charge. Results exclude
credentials and account identifiers. SSO/deployment roles use the SDK chain.
"""
import argparse
import json
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from farmsync.aws import check_approved_services


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check_approved_services()
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if report["all_passed"] else 1)
