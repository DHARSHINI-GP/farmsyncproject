# FARMSYNC project audit and manual acceptance checklist

> **Location verified — 17 October 2026:** Dedicated Builder-Location credentials pass STS. Existing FARMSYNC_PlaceIndex and FARMSYNC_RouteCalculator work for live reverse geocoding and driving routes. Survey 384 returned 10.71 km, 22.1 min and 72 geometry points; the browser displayed the same result. Cloud Location is enabled locally. No resources were created. Cloud geofence collections are unused; buffer audits remain local GIS. Redacted result: `scratch/aws-location-check.json`.

> **Latest live result — 17 October 2026, 14:44 IST:** Refreshed Builder-AI credentials pass STS. Live checks of Ministral 3B, Ministral 8B vision, Titan Text Embeddings and Titan Multimodal Embeddings all PASS in ap-south-1. The local session-token assignment was repaired without displaying secrets. Earlier InvalidClientTokenId results below are historical. This does not certify deployment or Amazon Location access. Redacted result: `scratch/aws-approved-check.json`.

> Latest: [HACKATHON_READINESS.md](HACKATHON_READINESS.md) supersedes earlier model/service assumptions and benchmark claims. The organizer-approved integration now uses Ministral 3B/8B and Titan models; live acceptance still requires refreshed Builder credentials.

Audit date: 17 October 2026. Scope: application source, both interfaces, bundled
datasets, model metadata, proposal claims, API behavior, dependency consistency,
automated tests, and browser smoke checks. This is a repository readiness review,
not certification of land ownership, agronomic recommendations, or error-free operation.

**Later AWS check:** live calls reached AWS after addressing local certificate
trust, but the configured credentials were rejected. See
[AWS_INTEGRATION_CHECK.md](AWS_INTEGRATION_CHECK.md) for exact responses, wiring
fixes, and the 47 passing focused regression tests. This supersedes the earlier
"live AWS not verified" entry below with an observed authentication failure.

## Release verdict

**Do not release as a fully verified production land-verification service yet.**
There is working GIS, PDF extraction, crop inference, local advisory retrieval,
workflow execution, and a usable demo. Important promised capabilities are either
conditional, simulated, or incomplete. The production blockers below remain.

## What the project actually provides

| Function | Implementation and limits |
|---|---|
| Interactive map | Leaflet polygons, roads, waterbodies, satellite toggle, parcel search and inspection. External tiles and CDN assets require connectivity. |
| Dataset coverage | 396 cadastral polygon records across **seven villages**, containing **304 distinct survey numbers**. This is not 396 uniquely identified parcels in one village. |
| Geometry analysis | GeoPandas/Shapely in EPSG:32644; polygon area, nearest road/waterbody/substation distance, a configurable waterbody distance threshold, FMB subdivision lookup. No PostGIS server is used. |
| Document analysis | PDF table/text extraction and a limited optional English EasyOCR path. Library selection and PDF uploads are available. A recognized header does not prove a PDF is parseable or authentic. |
| Ownership comparison | Name and extent comparison with bundled demonstration JSON records. This is **not live government ownership verification**. |
| Crop and growth stage | MobileNetV3 feature extraction plus a trained multitask head; 11 crop labels and 5 growth stages. Uses an indexed existing photograph, not a newly uploaded photo or live camera. |
| Escalation | Attempts a Bedrock teacher; otherwise uses augmentation of the same local model. The local fallback is not independent confirmation. |
| Advisory retrieval | Ten curated JSON entries covering seven crops, matched by crop and stage with FAISS or corpus lookup. Citation strings exist, but source documents and exact passages are not independently validated by these tests. |
| Natural-language interface | Regex entity/intent extraction into predefined task graphs; deterministic local report, optionally summarized through Bedrock. No general LLM planner is implemented. |
| Trust/evidence | Heuristic weighted trust score, accept/escalate/abstain decisions, provenance JSON and a Streamlit evidence inspector. These scores are not demonstrated probabilities of correctness. |
| Logistics | Amazon Location route/geocoding adapters. Without successful cloud calls, returns a labelled straight-line/Haversine estimate and assumed travel time. Local geofencing is a GIS distance check, not a real-time position tracking service. |
| Benchmark view | Stored 50-query results, assumed model costs, and simulated competitor behavior. This does not establish live GPT/Claude comparative accuracy or actual billed savings. |

Crop labels: Rice (Paddy), Coconut, Maize, Sugarcane, Banana, Sorghum, Cassava,
Marigold, Cotton, Groundnut, Mango. Stages: vegetation, full_growth, sown,
harvesting, flowering. Advisory coverage is smaller than classifier coverage;
unsupported crop/stage combinations should receive no advisory.

The dataset contains 3,422 JPEG files. The shipped training metadata reports
3,031 samples, a 2,435/596 split, and 91.28% best validation crop accuracy.
Those are artifact metadata, not an independent validation reproduced in this audit;
they do not establish growth-stage accuracy, calibration, OOD robustness, or field reliability.

## Corrections made in this audit

- Explicit survey numbers in AI questions override the active map selection.
- Subdivision routes accept slash-containing identifiers such as `384/1`.
- Document/GIS variance uses the GIS comparison rather than the demo registry delta.
- Discrepancy workflows execute supported single-parcel contracts instead of claiming batch extraction.
- Repeated cadastral/FMB identifiers refuse arbitrary first-row geometry selection.
- Map features retain their own polygon areas even when survey numbers repeat.
- Ambiguous or missing cadastral targets cannot trigger a borrowed field-photo inference.
- Sample audit statuses require explicit `FARMSYNC_DEMO_MODE=true`.
- Initial sample owner, acceptance, document-match, confidence and trace displays were cleared;
  selecting another parcel resets the prior audit.
- All parcel rows can be rendered; discrepancy filtering excludes merely unaudited rows.
- AI Markdown is sanitized, with plain text fallback; trace and route text is escaped.
- AI/orchestration/route POSTs use the existing access-control dependency; the UI sends the key consistently.
- Non-string API keys return unauthorized instead of causing comparison errors.
- PDF extraction rejects file paths outside the land-document directory, including resolved symlinks.
- API query lengths and origin coordinates are bounded.
- Blocking AI/orchestration/route work runs through FastAPI synchronous handlers instead of blocking the async event loop.
- AWS settings also refresh the vision client; obsolete Location session tokens are cleared.
- TLS verification is enforced in the AI and Location clients.
- AWS road requests explicitly request geometry; zero-valued origin coordinates are preserved.
- Route display tolerates missing turn instructions and labels estimated routes.
- Embedding loading uses local cached assets; fallback hashing is stable across processes.
  Small FAISS indices rebuild in memory instead of reusing incompatible/stale persisted vectors.
- Vision startup refuses inference without the trained head and cached backbone;
  it no longer silently classifies with an untrained head or downloads the backbone at startup.
- Teacher crop/stage/confidence responses are checked before accepting them.
- Added `FARMSYNC_OFFLINE=true` to prevent cloud initialization during offline operation.
- Report prose no longer equates an extent match with verified legal ownership.
- Telemetry separates measured node duration from route latency assumptions and exposes actual local tools.
- `/api/status` no longer presents hardcoded S3/DynamoDB resource names as integrations.
- Narrow-screen layout makes the map and AI panel reachable below the parcel list.
- Streamlit handles unavailable extent values, selects vision telemetry by task content,
  caches results across incidental rerenders, and keeps trust table values numeric.
- AI display rejects stale responses after a different selection/request; missing targets
  clear prior GIS metrics. An API key can be saved without supplying AWS credentials.
- Added `.env.example`; corrected the GeoPandas minimum for `union_all`, declared test/training dependencies,
  and removed the unused Python `marked` dependency.

## Remaining work, in release order

1. **P0 — Complete parcel identity.** Survey numbers repeat across villages/blocks:
   73 numbers have multiple records. For example, `176` appears in Peroorani,
   Umarikottai, and Melathattaparai. Add district/taluk/village/unit/block/survey/subdivision
   identity to API schemas, map selection, document joins, photo indexing, registry keys,
   and every workflow. Ambiguous lookups currently abstain safely; those parcels
   are not fully usable yet. Also validate photo location/village against the selected polygon.
2. **P0 — Government ownership integration.** Obtain and implement an authorized
   authoritative records connection, including provenance, freshness, and review of
   uncertain matches. Demo fixtures must not support legal ownership claims.
3. **P0 — Real deployment security.** Require authentication at the public gateway;
   do not rely on loopback detection behind a reverse proxy. The shared API key is
   not user/tenant authorization. Add per-user document isolation, rate and concurrency
   limits, upload quotas, durable storage, and controlled administration of global AWS
   credentials. Public GET endpoints currently expose library metadata and field photos.
   Never expose the Streamlit dashboard publicly without equivalent gateway controls.
4. **P1 — Model and evidence validity.** Independently validate crop/stage performance,
   confidence calibration, OOD behavior, and teacher disagreement. Validate each
   fertilizer/pest recommendation against the actual cited source and agronomic context.
   The 50m buffer is a configured project rule, not validated legal compliance for all sites.
5. **P1 — Robust document ingestion.** Add schema-specific table parsing, Tamil/scanned
   PDF coverage, survey/village linkage, extraction confidence review, resource/page
   limits, malformed-PDF checks, and immutable upload IDs. Same-name uploads currently
   overwrite the prior file; uploaded documents are globally visible in the library.
   Filename-based auto-selection is limited to a few hardcoded survey families.
6. **P1 — Workflow completeness.** Implement actual multi-parcel discrepancy/batch
   reporting; current execution checks one survey. Make environmental DAG nodes perform
   distinct operations instead of repeating the GIS handler. Add explicit failed-task
   handling and bounded retries/timeouts. Return verified unsupported-intent responses
   for requests the template system cannot perform (e.g. disease diagnosis).
7. **P1 — Cloud acceptance tests.** Verify Bedrock model access and regional IDs, teacher
   availability, IAM permissions, Location resources, actual route geometry, TLS/proxy
   configuration, credential expiry and service outages on the intended host. SDK client
   construction alone does not prove connectivity. Live cloud execution was not validated.
8. **P1 — Persistent operation.** Save audit results/history with stable unique IDs,
   timestamps and dataset/model versions; update map status from persisted audits.
   Add health/readiness probes, structured error logging without secrets, backups,
   observability, load testing, time budgets, and a deployment/rollback procedure.
   Current S3 and DynamoDB integrations are absent.
9. **P1 — Honest evaluation and telemetry.** Rebuild the benchmark after identity fixes,
   correct outdated expected acres/decisions, remove fabricated success defaults when
   benchmark files are missing, and record versioned test evidence. Replace assumed
   costs/latencies with actual service usage where advertised. Some planner route names
   remain historical model labels; local token counts are estimates, not consumed tokens.
10. **P1 — Reproducible environment.** Build a fresh virtual environment/container and
    a tested dependency lock. The current shared Python environment fails `pip check`:
    TensorFlow conflicts with installed NumPy/protobuf; MediaPipe conflicts with protobuf.
    Package caches presently hide some clean-host provisioning requirements.
11. **P2 — UI and documentation finish.** Vendor/pin CDN assets; improve remaining error,
    loading, stale-response and mobile states. Some descriptions still assume one village,
    fixed document counts, and crop-health diagnosis. Update all proposals, generated
    PDF/PPTX claims and screenshots before submission. Benchmark/dashboard labels must
    consistently distinguish simulations from measurements.

## Manual acceptance checklist

Start locally using `python -m uvicorn farmsync.server:app --host 127.0.0.1 --port 8000`.
Use `.env.example` to configure a deliberate offline/cloud mode. For network testing,
set `FARMSYNC_API_KEY` first and supply it through `X-API-Key` or the UI settings.

| Test | Steps | Expected result |
|---|---|---|
| Initial state | Open `/`; wait for polygons | 396 polygon records load. No completed ownership audit should appear before verification. |
| Search/list | Search `384`, then clear search and scroll | All matching records visible; list is not capped at 60. |
| Layer controls | Toggle cadastral, water, road and satellite controls; zoom/center | Correct layer changes, no frozen controls. Satellite requires tile network access. |
| Known unique geometry | Open `/api/parcel/384` | Area approximately 10.349 acres; real polygon/centroid and GIS distances. |
| Subdivision | Open `/api/parcel/384/1` | Actual subdivision geometry/area, not the parent's full boundary. |
| Missing survey | Ask `Inspect Survey 9999` while 384 is selected | Target stays 9999, no 384 area/photo substitution; no resolved geometry or invented advisory. |
| Ambiguous survey | Ask `Inspect Survey 176` | Geometry verification refuses; no arbitrary choice between three villages. This is pending identity support. |
| Explicit survey priority | Select 384; ask `Check Survey 381` | Result targets 381. Drawer metrics must correspond to that result, not stale 384 metrics. |
| Geometry-only audit | Ask `Check waterbody buffer for Survey 384` | GIS result, explicit no vision execution; any geometry acceptance does not imply ownership confirmation. |
| Document selection | Choose a listed notice and audit the exact survey shown in its table | Extracted fields and page checked manually against the PDF; GIS variance equals absolute area delta / GIS area × 100. |
| Missing document evidence | Ask the Survey 384 refuse-to-invent preset | If the chosen notice lacks 384, no owner/extent invented from another row. |
| Upload | Upload a small real PDF; then a `.txt`, renamed executable, empty and oversized file | Valid header accepted; unsupported/empty/oversize rejected; extraction may still need review for malformed/scanned PDFs. |
| Path traversal | POST a document path such as `../../.env` | No server file content read or exposed; extraction refuses path. |
| Crop prediction | Verify 384 and inspect displayed field photograph | Photo filename matches source evidence; crop/stage are model outputs, not CSV ground truth substituted into inference. |
| Unsupported evidence | Query a survey without a matching photo or supported advisory stage | No borrowed photo and no fabricated nutrient schedule. |
| Escalation/conflict | Use red-team teacher/conflict toggles | Trace identifies actual local TTA or Bedrock; conflict produces review/abstention as warranted. |
| Offline route | Click route with `FARMSYNC_OFFLINE=true` | Explicit estimate label and straight-line geometry; no missing-steps exception or invented turn instructions. |
| Cloud route | Repeat in cloud mode with validated resources | Actual road geometry/distance; failures clearly fall back to estimates. |
| Authentication | Configure key; POST without/wrong key, then correct key | 401 for missing/wrong keys; authorized request succeeds. Repeat from another machine through intended gateway. |
| UI output safety | Submit harmless HTML-like text within a question | Text is escaped/sanitized; no script execution from response rendering. |
| Streamlit | Run `python -m streamlit run farmsync/ui/app.py --server.port 8501` | Inspect result JSON, evidence graph, trust breakdown, telemetry and simulation notice. Full browser acceptance remains required. |
| Persistence | Run an audit; restart server and refresh map | Currently no durable audit history/status update. Treat as pending work, not a passing production feature. |

## Validation record

Validation results are recorded below after the final checks. No live AWS service,
public deployment, sustained load, independent crop evaluation, or full manual PDF
corpus comparison is certified by this audit.

| Check | Observed result |
|---|---|
| Full offline suite, earlier revision | 148 passed, one Starlette/httpx deprecation warning; 163.16 seconds. |
| Full offline suite after actual-model telemetry correction | 147 passed, one obsolete assertion failed because it required a Claude label for actual local TTA execution; 186.17 seconds. |
| Final affected-test rerun after correcting that assertion | **22 passed**, one deprecation warning; 96.25 seconds. Includes orchestration, all 15 new audit regressions, and parcel-status endpoints. The complete suite was not repeated after this focused fix. |
| Streamlit AppTest | Initial Survey 384, ambiguous Survey 176, and custom Survey 384 waterbody-buffer scenarios: **zero application exceptions**. Streamlit emits deprecated-width API notices. |
| Browser checks | Polygon list loads, narrow layout reaches AI/map, explicit unknown-survey query clears previous geometry, known Survey 384 report separates extent match from legal ownership, actual-tool telemetry renders. |
| Offline route in browser | Explicit `Estimate: 6.33 km · 13.6 mins`; straight-line/no-road-navigation guidance; missing turn instructions no longer cause an exception. |
| Python compilation | `python -m compileall -q farmsync tests`: passed. |
| Frontend syntax | Both inline JavaScript blocks extracted and checked with `node --check`: passed. |
| Patch formatting | `git diff --check`: passed. |
| Installed dependencies | `python -m pip check`: failed due to shared-environment TensorFlow/MediaPipe conflicts described above. |
| Live AWS | Not verified; attempted calls encountered the environment's blocked proxy. Cloud response-handling tests use mocks. |

Offline test settings: `FARMSYNC_OFFLINE=true`, `HF_HUB_OFFLINE=1`,
`AWS_EC2_METADATA_DISABLED=true`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
Use these settings deliberately; they do not test real cloud access.

The updated offline preview was started at `http://127.0.0.1:8017` to avoid
interrupting the pre-existing service on port 8000. Restart that existing service
before checking the new source on port 8000. Browser evidence is saved locally
at `scratch/audit-routing.png` (ignored by Git).
