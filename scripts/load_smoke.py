"""Bounded local load smoke; use an OFFLINE development server for no cloud charges."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import statistics
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8018")
    parser.add_argument("--output", default="scratch/load-smoke.json")
    args = parser.parse_args()
    if not args.base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise SystemExit("This script is restricted to a local offline test server")
    def request(path, body=None):
        start = time.monotonic()
        req = Request(args.base_url + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=190) as r:
                return r.status, json.load(r), (time.monotonic() - start) * 1000
        except HTTPError as exc:
            return exc.code, {}, (time.monotonic() - start) * 1000
    with ThreadPoolExecutor(max_workers=16) as pool:
        responses = list(pool.map(lambda _: request("/health/ready"), range(64)))
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = list(pool.map(lambda _: request("/api/jobs", {"query": "Check waterbody buffer for Survey 384"}), range(8)))
    results = []
    deadline = time.monotonic() + 190
    for code, job, _ in jobs:
        if code != 202:
            continue
        while time.monotonic() < deadline:
            _, run, _ = request("/api/jobs/" + job["run_id"])
            if run["status"] in {"COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"}:
                results.append(run["status"])
                break
            time.sleep(0.2)
    report = {"ready_requests": len(responses), "ready_successes": sum(r[0] == 200 for r in responses),
              "ready_median_ms": round(statistics.median(r[2] for r in responses), 2),
              "job_responses": [r[0] for r in jobs], "completed_jobs": results,
              "passed": all(r[0] == 200 for r in responses) and any(r[0] == 202 for r in jobs) and all(r[0] in {202, 429} for r in jobs) and len(results) == sum(r[0] == 202 for r in jobs) and all(r == "COMPLETED" for r in results),
              "scope": "Local bounded-load smoke, not a production capacity or availability guarantee"}
    from pathlib import Path
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
