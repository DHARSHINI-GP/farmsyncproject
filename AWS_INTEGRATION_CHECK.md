# AWS integration verification — 17 October 2026

> **Location verified — 17 October 2026:** Dedicated Builder-Location credentials pass STS. Existing FARMSYNC_PlaceIndex and FARMSYNC_RouteCalculator work for live reverse geocoding and driving routes. Survey 384 returned 10.71 km, 22.1 min and 72 geometry points; the browser displayed the same result. Cloud Location is enabled locally. No resources were created. Cloud geofence collections are unused; buffer audits remain local GIS. Redacted result: `scratch/aws-location-check.json`.

> **Latest live result — 17 October 2026, 14:44 IST:** Refreshed Builder-AI credentials pass STS. Live checks of Ministral 3B, Ministral 8B vision, Titan Text Embeddings and Titan Multimodal Embeddings all PASS in ap-south-1. The local session-token assignment was repaired without displaying secrets. Earlier InvalidClientTokenId results below are historical. This does not certify deployment or Amazon Location access. Redacted result: `scratch/aws-approved-check.json`.

> Latest: [HACKATHON_READINESS.md](HACKATHON_READINESS.md) supersedes earlier model/service assumptions and benchmark claims. The organizer-approved integration now uses Ministral 3B/8B and Titan models; live acceptance still requires refreshed Builder credentials.

**Verdict: live AWS integration is not working with the credentials tested.**
Checks used the project's environment / `.env` credentials in `ap-south-1`.
No credentials or AWS account identifiers were printed or saved in this report.
No AWS resources were created or changed.

## Live results

| Check | Result returned by AWS |
|---|---|
| STS credential validation | `InvalidClientTokenId` — HTTP 403 |
| Bedrock text / Converse | `UnrecognizedClientException` — HTTP 403 |
| Bedrock teacher / image InvokeModel | `UnrecognizedClientException` — HTTP 403 |
| Location reverse geocoding | `AccessDeniedException` — HTTP 401 |
| Location road routing with geometry | `UnrecognizedClientException` — HTTP 403 |
| Describe configured geofence collection | `UnrecognizedClientException` — HTTP 403 |

These results establish authentication failure for the tested credentials. They
do not establish whether the requested model access, IAM permissions or named
Location resources will work after credentials are refreshed.

The restricted tool network initially failed with `ProxyConnectionError`.
An approved run outside the sandbox then failed with `CERTIFICATE_VERIFY_FAILED`
(`unable to get local issuer certificate`). A temporary CA bundle combining the
SDK's roots with certificates already trusted by Windows allowed verified TLS
connections and produced the AWS responses above. **TLS verification was never disabled.**
The temporary bundle is `scratch/aws-system-ca.pem`; it is machine-specific and
ignored by Git. No system trust-store settings were changed.

## Code corrections made during this check

- Bedrock status now distinguishes a constructed client, an unverified connection,
  a failed call, and a successful call. Removed fabricated 274ms/42ms status metrics.
- Location reports initialized clients separately from successful geocoding and
  routing calls. Empty route geometry no longer counts as a usable live route.
- Fixed the UI's default model ID to `mistral.ministral-3-3b-instruct`; wired its
  selected model through the settings schema to the actual runtime model.
- Removed unverified alternative models from the dropdown. Cloud model access
  and region support must be checked for any additional configuration.
- Corrected the Ministral InvokeModel fallback to use `messages` rather than the
  old Mistral `[INST]` prompt format; set JSON content/accept headers explicitly.
- Authentication, throttling and transport failures no longer trigger an immediate
  duplicate request through the legacy API.
- Added bounded SDK connect/read timeouts and a single transport attempt for
  interactive AI, vision and Location calls.
- Vision now respects `AWS_DEFAULT_REGION` and `AWS_CA_BUNDLE` consistently, has
  configurable `BEDROCK_VISION_MODEL_ID`, respects offline mode when reconfigured,
  and clears the previous client before attempting a new configuration.
- Added a reproducible read-only live check script and mocked wiring regression tests.

AWS documents the configured Ministral ID, Converse/Invoke support and Mumbai
availability in its [Ministral 3B model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-mistral-ai-ministral-3b.html).
This verifies the text model configuration choice, not this account's model access.
The teacher ID / inference profile still needs a successful live invocation.

## What must happen next

1. Refresh credentials locally from the AWS access portal or the configured
   credential provider. Temporary sessions require a matching access key, secret
   key and session token from the same session. Do not paste secrets into chat.
2. Configure the trusted CA bundle required by the deployment/network, if TLS
   inspection applies. Keep certificate verification enabled.
3. Run `python scripts/check_aws_integration.py --output scratch/aws-live-check.json`
   from a network that can reach AWS. The check makes small, potentially billable
   model/geocoding/routing requests; its nonzero exit status means a check failed.
4. Once credentials pass STS, resolve any model authorization, inference profile,
   IAM or missing-resource errors exposed by the remaining checks. Do not use
   `setup_amazon_location.py` as proof of success: it currently catches individual
   errors and can still print an overall success message.
5. Restart the application with `FARMSYNC_OFFLINE=false` and repeat end-to-end
   verification through the API. The audit preview launched previously on port
   8017 was deliberately started with `FARMSYNC_OFFLINE=true`; changing `.env`
   alone does not change that running process.

## Remaining implementation limitations

- Runtime credential editing changes process-global credentials; it is unsuitable
  as a public, multi-user administration flow. Use deployment identities and a
  protected administration mechanism for production.
- Text and Location initialization currently gate on explicit environment keys;
  IAM role/profile/default-provider support needs to be made consistent with vision
  before deploying with a role-based identity.
- A successful prior call is historical evidence, not continuous availability or
  proof that a temporary session has not expired. Refresh/revalidate status as needed.
- The app's geofence audit uses local GIS. It does not evaluate moving devices
  against the cloud geofence collection. S3 and DynamoDB integrations are absent.
- The setup script is a provisioning utility, not a reliable readiness probe.

Live check output: `scratch/aws-live-check.json` (redacted, ignored by Git).
Automated checks: **47 passed in 73.79 seconds** using mocked/offline AWS paths:

```powershell
$env:FARMSYNC_OFFLINE='true'
$env:HF_HUB_OFFLINE='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python -m pytest tests/test_aws_wiring.py tests/test_amazon_location.py tests/test_bedrock_ai.py tests/test_vision.py -q
```

Python compilation, inline application JavaScript syntax, and `git diff --check`
also passed. These results verify code behavior and regression handling; they do
not override the six failed live checks above. The complete project suite was not
rerun for this focused AWS check.
