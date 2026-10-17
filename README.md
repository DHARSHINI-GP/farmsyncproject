# FARMSYNC

Task 1 prototype for the FarmwiseAI Product Challenge: evidence-driven orchestration
of crop photographs, land documents and deterministic geospatial analysis.

**Current release status:** the local application includes source-only document
extraction, real photo uploads, individual accounts, persisted jobs/history,
progress and human review. Organizer-only AWS adapters and Linux artifacts are
being validated separately; a prepared package is not a verified deployment.
See [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md) for every user-facing function
and [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for the cloud release gates.
Ownership remains explicitly unverified, using only the supplied datasets.

## Features

- Leaflet map with 396 polygon records across seven villages, satellite/road/water
  layers, parcel search and feature-specific selection.
- GeoPandas/Shapely area and proximity analysis in EPSG:32644, including FMB subdivision
  lookup. No PostGIS service is required.
- PDF upload and claim extraction, demonstration registry comparison and explicit
  missing/conflicting-evidence responses. The registry is not authoritative government data.
- Local MobileNetV3 crop/stage inference and optional approved Bedrock Ministral 8B
  vision escalation. Photos must match a parcel spatially before being treated as
  parcel evidence; explicitly selected unlocated photos are analyzed separately.
- Agronomy retrieval from the bundled ten-entry corpus with optional Titan Text
  Embeddings V2; local retrieval is available without AWS.
- Validated workflow DAGs and optional approved Bedrock domain planning, evidence
  provenance, heuristic trust breakdown, persisted progress and actual-tool traces.
- Owner-scoped uploads, passwords/sessions, saved audit versions and reviewer decisions.
- Multi-row document comparison, missing-field abstention and content-hash provenance.
- Local route estimates; Amazon Location is an optional extension requiring additional
  organizer permission and is disabled by default.

## Organizer-approved AWS configuration

The recovered access guide is in
`data/FAI_Product_Challange/FarmwiseAI_TCE_AWS_Access_Guide.pdf`.
Task 1 uses Mumbai (`ap-south-1`) and these models:

| Purpose | Model |
|---|---|
| Summaries | `mistral.ministral-3-3b-instruct` |
| Vision escalation | `mistral.ministral-3-8b-instruct` |
| Optional text retrieval embeddings | `amazon.titan-embed-text-v2:0` |
| Multimodal embedding access check | `amazon.titan-embed-image-v1` |

The shared core services are S3, Lambda, API Gateway, DynamoDB and CloudWatch Logs.
The AWS deployment adapter uses these services; successful live deployment must
be demonstrated independently of local tests. The S3/DynamoDB persistence and
Lambda/API Gateway adapters are implemented; live release acceptance is separate.
Use the assigned `fai-tce-team26-*` resource prefix and existing execution role when
deploying; do not create IAM roles or use another region to work around access denial.

Claude, cross-region profiles and GPU/EC2/RDS infrastructure are not enabled by this
Task 1 configuration. The router uses approved Ministral models and a local student.

## Run locally

Use a dedicated Python 3.10+ environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Do not overwrite an existing credential file. For offline operation, set
`FARMSYNC_OFFLINE=true`. Provision the trained crop head and cached MobileNetV3
backbone before enabling local image inference. The embedding model is optional;
stable local term hashing is used when it is unavailable.

```powershell
python -m uvicorn farmsync.server:app --host 127.0.0.1 --port 8000
python -m streamlit run farmsync/ui/app.py --server.port 8501
```

## Connect the assigned AWS session

Sign in with the organizer-assigned Identity Center username at
[the access portal](https://ssoins-6595aa2cbf056abd.portal.ap-south-1.app.aws), complete
MFA, select the team account and its Builder role. Copy the matching temporary
access key, secret and session token into local `.env`, or configure a signed-in
CLI SSO profile and set `FARMSYNC_AWS_PROFILE` to that profile name.
SDK deployment-role credentials are also supported. Never paste AWS secrets into
the application UI, chat, source code or a public repository.

Set `FARMSYNC_OFFLINE=false` and keep `AWS_DEFAULT_REGION=ap-south-1`. Windows
clients use the existing system-trusted certificates; other deployments can set
`AWS_CA_BUNDLE` to their organization's trusted bundle. TLS validation stays enabled.

```powershell
python scripts/check_aws_integration.py --output scratch/aws-live-check.json
```

The explicit check validates STS first, then makes small model calls only when
credentials pass. It creates no resources. A nonzero exit status means a check
failed. The UI's **Cloud service status** panel exposes the same live checks and
can reload refreshed local credentials without accepting AWS secrets in the browser.

Set `FARMSYNC_EMBEDDINGS_PROVIDER=bedrock` to use Titan for advisory retrieval;
local is the default. Cloud embedding failures rebuild a fully local index rather
than mixing incompatible vectors.

## Validation and limitations

```powershell
$env:FARMSYNC_OFFLINE='true'
$env:HF_HUB_OFFLINE='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python -m pytest -q
```

Tests include mocks and controlled scenarios; they do not prove live model access,
legal ownership, agronomic correctness or deployment reliability. Stored benchmark
results predate the corrected photo/parcel association and must be re-evaluated.
Costs are estimates, and competitor baselines are simulations.

Read [PROJECT_AUDIT.md](PROJECT_AUDIT.md) for the manual checklist and broader
production gaps. Configure authentication, protected data access, durable storage,
monitoring and the deployment target before any public release.

Team PRIME · Team-26 · TCPC-2026-00071 · Thiagarajar College of Engineering.

### Grounded audit reports

Bedrock selects a constrained report focus; the server renders report facts from
actual GIS, document and vision results. Free-form model prose is not published
as verified evidence. The separate Location role supports verified cloud reverse
geocoding and road routing; local GIS computes parcel buffer checks. See
`HACKATHON_READINESS.md` for live results and remaining deployment gates.
