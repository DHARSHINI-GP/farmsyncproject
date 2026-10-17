# Organizer requirements and current readiness

> **Location verified — 17 October 2026:** Dedicated Builder-Location credentials pass STS. Existing FARMSYNC_PlaceIndex and FARMSYNC_RouteCalculator work for live reverse geocoding and driving routes. Survey 384 returned 10.71 km, 22.1 min and 72 geometry points; the browser displayed the same result. Cloud Location is enabled locally. No resources were created. Cloud geofence collections are unused; buffer audits remain local GIS. Redacted result: `scratch/aws-location-check.json`.

> **Latest live result — 17 October 2026, 14:44 IST:** Refreshed Builder-AI credentials pass STS. Live checks of Ministral 3B, Ministral 8B vision, Titan Text Embeddings and Titan Multimodal Embeddings all PASS in ap-south-1. The local session-token assignment was repaired without displaying secrets. Earlier InvalidClientTokenId results below are historical. This does not certify deployment or Amazon Location access. Redacted result: `scratch/aws-approved-check.json`.

Reviewed 17 October 2026 against the recovered organizer documents inside the
original `FAI_Product_Challange.zip`. These documents were absent from the
previous extraction and are now restored under `data/FAI_Product_Challange/`.

## Source of requirements

- `FarmwiseAI_TCE_AWS_Access_Guide.pdf`: access portal, Builder role, allowed
  services/models, Mumbai restriction, naming rules and event budget.
- `FAI_Task_Details_Requirements.pdf`: Task 1 has no separate dataset; choose
  relevant resources from Tasks 2–6 and independently process/validate them.
- `FAI_Product_challange_TCE_Doubt_session.xlsx`: a list of participant questions,
  not official answers or grants of extra service permissions. Team-26 is PRIME.
- `Initial_review.xlsx`: review scheduling/progress entries, not AWS permissions.

The resource guide says the original challenge brief/problem statement remains
the primary reference. No separate official Task 1 problem statement was found
in this archive. The project's proposal files are participant-authored drafts,
not evidence of organizer-provided access or successful deployment.

## AWS access matrix

| Organizer provision | Application behavior |
|---|---|
| Assigned Identity Center username + Builder role | Server SDK credential chain supports matching temporary credentials, SSO profile or deployment role. No IAM users/roles are created. |
| Mumbai only (`ap-south-1`) | Client factory rejects other regions. Cross-region model/profile IDs are rejected. |
| Ministral 3B Instruct | Bedrock Converse for executive summaries. |
| Ministral 8B Instruct | Approved multimodal teacher via Converse image blocks, replacing the unsupported Claude path. |
| Titan Text Embeddings V2 | Optional 256-dimensional advisory embeddings with caching; local retrieval remains default. |
| Titan Multimodal Embeddings | Explicit live access probe uses the approved model. No production similarity feature is claimed. |
| S3, Lambda, API Gateway, DynamoDB, CloudWatch Logs | Available platform building blocks. This repo does not yet contain a deployed serverless stack or S3/DynamoDB persistence. Availability alone is not an implementation requirement for every service. |
| `fai-tce-teamXX-*` naming | Optional provisioning uses Team-26 names; shared `FAI-TCE-LambdaExecutionRole` must be reused if a serverless deployment is built. |
| USD 100 event budget | No resources created during this work. Diagnostic stops before model calls if STS fails. Budget is an alert threshold, not a guaranteed cap. |
| Category-specific access | Task 1 configuration does not assume Textract, Rekognition, Claude, EC2, RDS or Amazon Location access. Local PDF/OCR, vision and GIS remain available. |

Amazon Location is absent from the supplied Task 1 service list. Its adapter is
retained as an explicitly disabled extension; it requires additional organizer
approval and `FARMSYNC_AMAZON_LOCATION_ENABLED=true`. Local geofencing and estimated
routes do not require it and are labelled accordingly. Provisioning now checks
failures accurately and never creates resources by default.

## Changes made after reading the guides

1. Centralized clients in `farmsync/aws.py`: Mumbai enforcement, approved model
   IDs, default credential chain, SSO profile support, verified TLS using existing
   Windows trust, bounded timeouts and attempts.
2. Replaced the Claude escalation request/route with Ministral 8B and a compatible
   Converse image payload. Local TTA stays labelled as reuse of the student.
3. Added optional Titan text retrieval. Failed cloud indexing falls back to one
   complete local index; vectors from different models are never mixed.
4. Added STS-first diagnostics and a service-status panel. AWS secrets are no
   longer requested in the UI. Legacy runtime credential editing is disabled by
   default; the protected live-check endpoint reloads refreshed local credentials.
5. Protected all `/api/` dataset endpoints from unauthenticated network clients.
   Local development remains available; a configured application key is enforced
   locally too. Photo previews fetch authenticated blobs. Image serving is limited
   to the indexed library, closing Windows backslash path traversal.
6. Added stable feature IDs built from administrative identity and polygon geometry.
   All 396 map records are selectable independently. A bare repeated survey number
   still refuses to choose a village arbitrarily. API and workflow requests carry
   the selected identity through GIS, route and extent checks.
7. Added village checks to demonstration registry joins and actual polygon checks
   for photo association. All 18 Survey 384 photo records in the supplied photo
   dataset have coordinates outside its mapped polygon. Their shared survey number
   is not proof that they depict this parcel.
8. Explicit photo selection supports image-only classification/advisory without
   asserting verified parcel location. Unlocated photos do not increase parcel
   evidence coverage. Geometry-only checks can still succeed independently.
9. Corrected documentation and labelled old proposals as historical. Removed crop
   health/diagnosis claims from UI prompts; the model predicts crop and growth stage.

## Earlier AWS acceptance gate (resolved by refreshed credentials)

The latest live diagnostic reached AWS with TLS verification enabled and returned
`InvalidClientTokenId` for STS. It skipped all model calls after that failure.
Results are in `scratch/aws-approved-check.json`. There is no configured SSO profile
or cached SSO session on this machine. The stored temporary credentials have not
been refreshed during these checks.

**Required human action:** sign in to the assigned account and Builder role,
complete MFA, and refresh all three local temporary credential values together.
An application cannot renew a personal MFA session without the account holder.
No cloud feature is marked verified merely because a boto3 client exists.

### Sign-in steps

1. Open `https://ssoins-6595aa2cbf056abd.portal.ap-south-1.app.aws`.
   The guide also gives `https://d-9f67598e80.awsapps.com/start` as a fallback.
2. Use the organizer-assigned Identity Center username, not a root/account email.
   Complete first-login verification, password setup and MFA if requested.
3. Open the assigned team AWS account and choose its AI/Agentic AI Builder role.
   The Cost Viewer role is for billing review, not application invocation.
4. Choose **Access keys** for that role and copy a matching access key, secret key
   and session token into `.env` on this computer. Do not send them in chat.
5. Save the file. The new **Cloud service status → Check live AI services** action
   reloads those values, runs STS, then tests the four approved models.
6. If username, account or Builder role is missing, use organizer support. Do not
   create new IAM permissions or switch to another AWS region to bypass denial.

Alternative: configure a signed-in AWS CLI SSO profile and set
`FARMSYNC_AWS_PROFILE` to its name. Profiles take precedence over stale environment
keys in the shared factory. In a supported serverless deployment, use the existing
execution role rather than interactive SSO credentials.

## Manual acceptance tests added to the earlier checklist

- Select each of the three Survey 176 polygons. The drawer must show its actual
  village and area; routing and buffer checks must use that polygon's feature ID.
- Query a repeated survey number without choosing a parcel: no arbitrary geometry.
- Run Survey 384 with the default spatially matched-photo setting: no borrowed
  crop photo, no invented crop, and missing evidence is visible.
- Select a photo explicitly and run classification: crop/stage can appear, but
  the badge/report must say location unverified unless coordinates match.
- Open Cloud service status: no AWS secret fields. Run live checks with an invalid
  session: credentials fail; model checks remain NOT_RUN rather than appearing live.
- Refresh credentials locally and repeat: STS and each approved model must return
  PASS before claiming live AWS acceptance. No Claude or cross-region fallback.
- Fetch `/api/parcels`, `/api/images` or GeoJSON from another machine without an
  application key: 401; with the correct configured key: authorized access.

## Remaining release work

- Builder-AI live checks now pass; temporary sessions still require renewal when they expire.
- Government ownership is still demonstration-only; scanned/Tamil extraction and
  document-to-village validation need further review. Do not use this as legal verification.
- Arbitrary new image uploads are not implemented; the UI currently selects from
  the provided indexed dataset. Image-only evidence is separate from parcel confirmation.
- Re-evaluate the benchmark after correcting photo/parcel associations. Stored
  100% results and simulated cost savings do not validate the corrected configuration.
- The event resource guide does not establish every functional requirement of the
  missing primary Task 1 brief. Resolve that before claiming full challenge compliance.
- Public deployment still needs a selected host, durable audit/document storage,
  per-user authorization, logs/monitoring, backups and load testing. No serverless
  resources have been provisioned, and restricted data has not been published.

## Final validation (17 October 2026)

- Full offline regression suite: **173 passed**, one dependency deprecation warning
  from Starlette/httpx. These tests do not establish live AWS availability.
- Streamlit AppTest: initial screen, Scenario 3 and a custom 100 m buffer query
  completed with zero application exceptions. Deprecated layout arguments were
  subsequently replaced with the supported width setting and rechecked.
- Browser: cloud checks correctly show STS failure and all four models NOT_RUN;
  AWS secret inputs are absent. Survey 176 in Umarikottai resolves to 1.785 acres,
  separately from its same-number records in other villages.
- Source compilation, inline JavaScript syntax and Git whitespace checks passed.
- Earlier live AWS gate failed with InvalidClientTokenId; the refreshed session now
  passes STS and all four approved model checks. No AWS resource was created.
  Deployment acceptance remains outstanding; separate Amazon Location role checks now pass.


## Additional Location role shown in the access portal

The user portal now shows `FAI-TCE-Team26-Builder-Location`, separate from the
Builder-AI and Cost-Viewer roles. The application supports a dedicated Location
SSO profile (`FARMSYNC_LOCATION_AWS_PROFILE`) or all three `LOCATION_AWS_*`
temporary credential entries. These values do not overwrite the AI session.
The local `.env` has empty entries prepared for this session. Location is now enabled and its credentials, existing resources, reverse
geocoding and routing have passed live checks. The original Task 1 guide did not
list this additional grant; the portal assignment is newer evidence of access.

Location follow-up regression: **42 passed**; inline JavaScript syntax check passed.

## Live combined-workflow finding and correction

A real Bedrock-generated report invented government portal checks, legal ownership,
water-rights checks and satellite inspection. Prompts alone did not prevent this.
The application now permits model output to select only one of four report-focus
labels. Displayed findings are rendered deterministically from tool evidence;
free-form model prose and arbitrary JSON fields are not published as audit facts.
Evidence limits explicitly identify demo ownership data and absent live government
checks. Added regression cases cover invented prose, extra JSON claims, invalid
focus values and valid focus selection. Small-screen drawer sizing was also fixed
so the panel no longer blocks the Ask AI button.

Final expanded regression suite: **180 passed**, one Starlette/httpx deprecation warning.
The live grounded report successfully invoked Ministral 3B and explicitly reported
DEMO_MATCH_NOT_OFFICIAL_VERIFICATION and VERIFIED_ABSTAIN for Survey 384.
A later wording fix removes blank crop/advisory values and prevents demo registry
names being substituted for unextracted document claimants.
