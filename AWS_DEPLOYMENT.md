# Organizer-only AWS deployment

The intended production target is Lambda, S3, DynamoDB, API Gateway and CloudWatch
Logs in **ap-south-1**. Docker/Compose files are optional local packaging and are
not the selected public hosting path. No EC2, ECR, RDS, new IAM role, other region
or unapproved foundation model is required by this deployment adapter.

## Architecture and limits

- A small Python 3.12 API Lambda serves the interface, authentication, source GIS
  snapshots, uploads, history and review endpoints. ML/GIS imports stay out of it.
- API Gateway uses HTTPS. Individual HttpOnly/Secure/SameSite cookies protect
  every data API. Only login/status and non-sensitive health routes are public.
- Private S3 holds versioned evidence, model/data bundles and large result JSON.
  Browser uploads use short-lived, owner-scoped POST policies with a 15 MB cap;
  completion validates the actual PDF/image before recording an immutable asset.
- DynamoDB stores users, hashed sessions, assets, jobs, events, quotas and review
  records. A conditional state transition prevents duplicate worker execution.
  Two deployment-wide processing slots bound accepted analysis concurrency.
- A separate async Lambda downloads a SHA256-pinned CPU ML/GIS bundle into `/tmp`.
  This is a disposable model cache, never the database or the evidence archive.
  Jobs survive browser disconnects. Progress is polled from persisted events.
- The worker uses 8 GB memory, 10 GB temporary storage and a 15-minute invocation
  limit. Individual analysis steps have cancellation/deadline checks and bounded
  AWS timeouts. A terminated invocation is surfaced as interrupted on inspection.
- S3 public access is blocked, encryption/versioning enabled; staging expires
  after one day. DynamoDB PITR is enabled. Lambda logs retain 14 days.
- The configured daily job allowance and API throttle are **not a dollar cap**.
  The organizer's Cost-Viewer dashboard remains necessary for the event budget.

This design follows the [Lambda package and temporary storage limits](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html),
[AWS's S3 model-loading pattern](https://aws.amazon.com/blogs/compute/deploying-ai-models-for-inference-with-aws-lambda-using-zip-packaging/),
and [S3 POST policy limits](https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTConstructPolicy.html).

## Build and release gates

Run from the repository root. Dependencies are downloaded from PyPI/PyTorch's
official CPU index. The resolved Linux wheel hashes are recorded in
`aws/worker-linux.lock.txt` and `aws/api-linux.lock.txt`; Windows DLLs are excluded.

```powershell
python scripts/aws_inventory.py
python scripts/check_aws_integration.py --output scratch/aws-live-check.json
python scripts/provision_models.py --vision --embeddings --ocr
python scripts/build_aws.py --download-wheels
python scripts/build_aws.py --download-wheels --api-wheels
python scripts/build_aws.py --snapshot-only
python scripts/build_aws.py --reuse-snapshot
python scripts/build_aws.py --api-wheels --reuse-snapshot
python scripts/deploy_aws.py
```

The last command prints a plan and changes no cloud resources. Builds are private
under ignored `.runtime/aws-build`. Source changes invalidate the release hash;
rebuild with `--refresh-code` (and refresh the snapshot after dataset/GIS changes).

The explicit `python scripts/deploy_aws.py --apply` operation stages private
resources and tests the worker on the actual Linux Lambda runtime. It uses only
the existing **FAI-TCE-LambdaExecutionRole** and stops on permission denial. It
does not create or modify IAM permissions. A successful local test or successful
credential check does not satisfy the Linux worker gate.

After private validation, create a real operator account interactively:

```powershell
python scripts/manage.py --cloud create-user YOUR_USERNAME --role admin
```

Then review and run the separately explicit public publication operation:

```powershell
python scripts/deploy_aws.py --apply --publish-api
```

It refuses a stale/unverified worker or missing administrator. The resulting URL
is in the ignored deployment state file. Publication still requires authenticated
browser tests of source uploads, analysis, history, cancellation and review on
that URL. No public deployment has been certified by the local tests.

## Identity and organizer permissions

Temporary development credentials belong in `.env` or SSO profiles, never Git,
browser settings, build archives or Lambda environment variables. Lambda uses
the organizer's execution role and automatic SDK credential renewal. Both roles'
development sessions require **access ID, secret and matching session token**.

The execution role must be allowed to access this deployment's S3/DynamoDB,
invoke the worker, write logs, use the four approved Bedrock models and access the
assigned Location index/calculator. The Builder-Location development session does
not automatically grant Location access to a Lambda execution role. If denied,
the organizer must grant it; do not copy short-lived user sessions into Lambda or
create an alternative IAM role to bypass the restriction. Local route fallbacks
remain explicitly labelled estimates.

## Recovery and operations

- Local development: `scripts/manage.py backup DIRECTORY` captures SQLite and
  checksummed evidence; `restore BACKUP NEW_DIRECTORY` verifies both, restores
  ownership links and revokes old sessions. This round trip is regression-tested.
- Cloud: PITR and S3 versions provide recovery primitives. An actual restore to
  a new table/bucket and an authenticated replay must be tested before production
  acceptance. Local restore tests do not establish cloud recovery readiness.
- Every job stores status, original references, progress, result and errors.
  Failed/abstaining results enter human review. A reviewer decision cannot turn
  demonstration ownership data into an authoritative government record.
- Evidence can be archived/restored through owner-scoped APIs. Permanent deletion,
  retention periods and legal audit access require an operator-approved data policy;
  the application does not silently purge land records.
- Preserve each release bundle, hashes and deployment state. Rollback must select
  the previous verified artifact, update both functions, warm the worker and repeat
  readiness/authenticated smoke checks. No rollback/restore has been proven live yet.

## Current acceptance boundary

Local regression, mock AWS tests, generated scanned-page OCR and local load tests
are separate evidence. Live credentials, execution-role grants, target-Linux
initialization, public HTTPS workflows, cloud restore and actual cost/latency
measurements remain deployment gates until their checks pass. Never describe a
prepared artifact or constructed SDK client as a working public deployment.
