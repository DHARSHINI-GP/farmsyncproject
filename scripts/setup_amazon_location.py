"""Optional Amazon Location extension, only after explicit organizer approval.

The Task 1 access guide does not include Amazon Location. The default invocation
does not create resources. Pass --create only after additional access is granted.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from farmsync.aws import create_client, safe_error


def setup_amazon_location(create=False):
    if os.getenv("FARMSYNC_AMAZON_LOCATION_ENABLED", "false").lower() != "true":
        print("Amazon Location is not provided for Task 1. Additional organizer approval and explicit enablement are required.")
        return False
    client = create_client("location")
    if client is None:
        print("Cloud access is disabled or no AWS credentials are available.")
        return False
    resources = [
        ("places", "IndexName", os.getenv("AMAZON_LOCATION_INDEX", "fai-tce-team26-places"), client.describe_place_index, client.create_place_index),
        ("routes", "CalculatorName", os.getenv("AMAZON_LOCATION_ROUTER", "fai-tce-team26-routes"), client.describe_route_calculator, client.create_route_calculator),
        ("geofences", "CollectionName", os.getenv("AMAZON_LOCATION_GEOFENCE", "fai-tce-team26-geofences"), client.describe_geofence_collection, client.create_geofence_collection),
    ]
    results = {}
    for label, key, name, describe, provision in resources:
        if not name.startswith("fai-tce-team26-"):
            results[label] = {"status": "FAIL", "error": "Resource name must use the assigned fai-tce-team26- prefix"}
            continue
        try:
            describe(**{key: name})
            results[label] = {"status": "PASS", "action": "existing"}
        except Exception as exc:
            code = safe_error(exc)
            if create and code == "ResourceNotFoundException":
                try:
                    options = {key: name, "Description": "FARMSYNC optional organizer-approved extension"}
                    if label != "geofences":
                        options["DataSource"] = "Esri"
                    provision(**options)
                    describe(**{key: name})
                    results[label] = {"status": "PASS", "action": "created_and_described"}
                except Exception as failure:
                    results[label] = {"status": "FAIL", "error": safe_error(failure)}
            else:
                results[label] = {"status": "FAIL", "error": code}
    success = all(row["status"] == "PASS" for row in results.values())
    print(json.dumps({"all_resources_verified": success, "resources": results}, indent=2))
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true", help="Create missing resources after organizer approval")
    args = parser.parse_args()
    raise SystemExit(0 if setup_amazon_location(args.create) else 1)
