> **Historical audit snapshot; implementation has changed.** Source-field fabrication
> has been replaced, and uploads/accounts/history/review/planning/operations work has
> been added. Read [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md) and
> [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for current functionality and release gates.
> The findings below document the original issues, not the current test result.

# FARMSYNC: promise coverage and production gaps

Reviewed 17 October 2026. This assessment compares the current source with
`FARMSYNC_Final_Submission.md`, `FARMSYNC_Proposal_Final.md`,
`FARMSYNC_IMPLEMENTED_PROPOSAL.md`, and the current application documentation.
The proposals are historical promises, not proof of implemented behavior.
The primary official Task 1 problem statement is still not separately identified;
this is not a certification of complete organizer requirement compliance.

## Verdict

The project has a working local integration of GIS, indexed crop photographs,
PDF parsing, workflow execution, evidence scoring and AWS services. It is not yet
a complete implementation of all proposal promises or a production service.

Earlier live checks passed STS, Ministral 3B, Ministral 8B vision, Titan text and
multimodal embeddings, and the separate Location role's geocoding and road routing.
Those are point-in-time integration checks, not an uptime or model accuracy guarantee.
Titan multimodal embeddings currently have an access probe, not a user-facing
similarity-search feature. S3/DynamoDB/serverless deployment are not implemented.

The latest full regression run passed 180 tests, but the controlled parser probe
below uncovered an additional correctness gap outside that suite's coverage.

## Highest-priority correctness finding: document evidence can be invented

**Release blocker; confirmed by a controlled parser probe.**

In `farmsync/documents/extractor.py`, table-parser branches fill an absent owner
with `Ramesh Kumar` for Survey 384, or a name from the demo registry for other
surveys. The regex parser also supplies those names and can replace absent
document extent with an area from the cadastral index. The result can still be
labelled `EXTRACTED_FROM_REAL_PDF` with a fixed 0.92 or 0.96 confidence.

Probe: a mocked PDF table row `['384', '10.00', '']`, containing no owner name,
returned `extracted_owner = Ramesh Kumar`, `ocr_confidence = 0.96`, and
`status = EXTRACTED_FROM_REAL_PDF`. The probe uses mocked PDF content, not a claim
that every real PDF takes this path. Redacted reproduction output is saved in
`scratch/document-evidence-gap.json`.

This contaminates independence: a registry-derived value cannot also count as
independent document evidence against that same registry. The earlier generated
report guard blocks free-form LLM inventions, but cannot correct fabricated
upstream tool values. Real extracted names must be supported by actual source text.

Completion criteria:

- Missing owner and extent remain null, with field-level extraction status.
- Demo registry lookup never populates document-extracted fields.
- Every positive claim identifies its PDF, page, source text/table cell and unit.
- Area parsing validates column semantics, units, subdivisions and village identity.
- Parser scores are described honestly; fixed constants are not measured accuracy.
- Regression tests cover missing names, absent extent, repeated survey numbers,
  unrelated numbers, wrong villages, conflicting units and scanned/Tamil pages.
- Re-run the benchmark, trust decisions and UI checks after correcting the parser.

## What is still missing from the promises

| Promise | Current implementation | Remaining work / honest scope |
|---|---|---|
| Upload text, PDFs and new field photographs | Text and protected PDF upload work. Photo selector uses the indexed dataset. | Add actual image upload/capture, validation, metadata, storage and explicit parcel association. |
| Verify registered owner | Demo JSON registry comparisons; no authoritative government connection. | Authorized authoritative data integration and provenance, or explicitly retain demo-only ownership scope. |
| Reliable scanned land-document extraction | pdfplumber text/table heuristics plus optional EasyOCR. Reader is English-only; scanned fallback inspects images on the first two pages. | Correct the evidence fabrication above; support and evaluate required languages, complete page rendering and extraction, units and layouts. PaddleOCR is not the current implementation. |
| Generic agentic planning from arbitrary requests | Regex/keyword intent extraction chooses predefined workflow templates. | Implement constrained dynamic planning with validated tool contracts and unsupported-request handling, or narrow the claim to template-based orchestration. |
| Batch discrepancy intelligence across a document | Discrepancy requests currently execute the single-parcel advisory template. | Extract all relevant document rows, resolve identities, run batch joins and produce a batch discrepancy report. |
| Adaptive verified-utility routing | Actual scoring and confidence-triggered escalation exist. Candidate costs, quality, risk and latency profiles are hand configured. | Validate routing against measured data, filter unavailable/unsupported candidates and demonstrate utility improvement. Registry alternatives are not proof of executable adapters. |
| Calibrated, model-agnostic trust | Schema/evidence checks and abstention exist. Weights, thresholds and calibration proxies such as 0.92 are coded constants. | Fit/evaluate calibration on independent labelled cases; measure false accept/abstain rates. FTS is not a certified probability of correctness. |
| Independent teacher verification | Approved Ministral 8B image calls work; offline TTA reuses the student and is labelled accordingly. | Evaluate teacher benefit, disagreements and failure handling on actual crop cases. Student TTA is not independent evidence. |
| Reliable crop/stage recognition on unseen fields | Trained MobileNetV3 head: 11 crops, five stages. Metadata reports 91.28% crop validation accuracy and grouped split. | Reproduce results, verify group identity, measure each crop and growth stage, calibration and out-of-distribution behavior on separate field data. Model metadata alone is not independent validation. |
| Grounded stage-specific agricultural advice | Ten JSON corpus entries covering seven crops, with citation strings. Optional Titan text retrieval. | Verify source publications/pages, broaden coverage, preserve source versions and explicitly report unsupported crop-stage pairs. No full source-document ingestion pipeline is implemented. |
| Crop health/diagnosis | Crop and stage inference, no validated health/disease diagnosis model. | Remove residual health promises or build and independently evaluate that capability. |
| Source-traceable, verified final answer | In-memory evidence graph and deterministic report from tool output. Bedrock now selects a finite report focus. | Fix upstream evidence fabrication; add durable source/run identifiers and provenance validation. Broad free-form agronomic/legal synthesis is deliberately constrained. |
| Live task graph and execution monitoring | Task graph and measured step durations are returned after synchronous execution. Nodes run sequentially. | Stream per-step progress for genuine live status; add job lifecycle/cancellation. If parallel execution is claimed, implement bounded dependency-aware scheduling. |
| Escalation to human review | Decision flags and explanations exist. | Add assigned review cases, source inspection, comments, resolution and reviewer audit history. A flag is not a complete review workflow. |
| More than 50% savings with no accuracy loss / 100% benchmark results | Historical benchmark labels, simulated competitor baselines and assumed per-route prices. | Rebuild ground truth after photo/parser corrections, evaluate held-out queries, and report measured costs/latencies with clearly identified simulated comparisons. Existing figures do not substantiate those promises. |
| PostGIS/SQL and named frontier models | Current tools are GeoPandas/Shapely, demo JSON, MobileNet and approved Ministral/Titan models. | These substitutions can be legitimate. Rewrite proposal/slides around actual behavior; do not install old providers or PostGIS merely to match obsolete names. |
| Fully deployed production stack | Local FastAPI and Streamlit; no public production stack in the repository. | Select a deployment target, package artifacts, provision within granted permissions and test the deployed service. |

## Data gap affecting the primary demonstration

All 18 photo records labelled Survey 384 checked earlier have coordinates outside
its cadastral polygon. Identical survey numbers do not establish identical land
identity. The corrected default must therefore avoid confirming a parcel crop.
Provide genuinely linked photos or use an explicitly labelled image-only demo.
Do not make the demo appear successful by weakening location matching or forcing
an ACCEPT result. Repeated survey numbers across villages also require complete
administrative/feature identity in document and photo joins.

## What a real-world deployed service still needs

| Area | Current gap | Release acceptance condition |
|---|---|---|
| User identity and authorization | Shared API key/local bypass; no individual users, roles or per-record isolation. Streamlit has a separate security boundary to configure. | Authenticated sessions, least-privilege roles and server-enforced access to each user's records. A shared key may suit a restricted demo, not a multi-user records service. |
| Production authentication enforcement | Local-loopback fallback exists when no app key is set. API keys are also accepted in URL query parameters. | Production startup must fail when required auth is absent; verify reverse-proxy behavior and keep credentials out of URLs and logs. |
| Durable application data | No database-backed audit runs, users, review cases, result history or object storage integration. Uploads live on local disk; process state/caches are in memory. | Persistent records and protected file storage, migrations, run IDs, model/source versions and reproducible results after restart. S3/DynamoDB are available options, not mandatory services to tick off. |
| Safe file lifecycle | Same sanitized PDF filename opens with `wb`, so a later upload can overwrite it. All uploads share a folder. | Unique file IDs, tenant ownership, immutable versions/checksums, retention/deletion and safe parsing limits. Auto-index refresh for newly uploaded documents must be verified; the index is built at startup. |
| Deployment packaging | No Dockerfile, CI workflow or infrastructure definition found. Many Python dependencies use lower bounds only; model/backbone/OCR caches need provisioning. | Reproducible pinned runtime, packaged required artifacts, cold-start/clean-install verification, deploy procedure and rollback. Check suitability before assuming this Torch/GIS application fits a particular host. |
| Credential lifecycle | Interactive temporary sessions currently enable local live calls. | Deployment identity or supported credential renewal; tested expiration behavior for both AI and Location sessions. Keep all secrets outside shipped client assets and source control. |
| Capacity and long-running requests | Synchronous work, sequential nodes, process-global clients/caches and no background job queue/admission limits. | Defined concurrency target, bounded jobs, isolation, load/soak testing, deadlines and safe cancellation/retry rules. Measure worker/model memory. |
| Resilience and dependency failures | Some bounded SDK calls and local fallbacks exist; full operational recovery has not been demonstrated. | Tests for expired sessions, access denial, throttling, timeouts, missing models, corrupt files, unavailable maps and restart recovery. No fallback may claim cloud success or verified evidence falsely. |
| Observability | UI telemetry and console messages; no persistent operational metrics/alerting stack. `/api/status` reports ONLINE without being a comprehensive readiness gate. | Structured redacted logs, request IDs, liveness/readiness checks, dependency/error/latency metrics, alerts and actionable runbooks. |
| Cost control | Estimated route costs do not include a complete measured per-request cloud bill. No quotas/rate limits or application spending circuit breaker found. | Attribute actual model tokens and Location calls, enforce per-user/request limits, monitor spend and configure budget responses. |
| Backup and recovery | No demonstrated backup policy or restore exercise for uploaded documents and results. | Defined retention, backups, tested restoration and recovery objectives appropriate to the actual use. |
| Privacy and dataset handling | Source data remains local; production controls are not complete. | Confirm authorized publication/use, restrict access, minimize metadata disclosure and implement retention/deletion and access auditability. |
| Frontend reliability | Runtime CDN dependencies include unpinned Tailwind, Lucide latest and Marked. Full mobile/accessibility coverage is not established. | Reproducible frontend assets, accessible controls, responsive tests and useful failure states for map/CDN/network errors. |
| Operational product workflow | No durable case history, human review queue or user-facing audited export flow. | Add these if real users need to revisit/share/resolve cases; do not mistake installed report-generation libraries for implemented product flows. |

## Recommended implementation order

1. **P0: make evidence truthful.** Remove invented document fields, validate units
   and identities, test negative cases, and reassess trust decisions.
2. **P0: make public access controlled.** Choose single-user restricted demo versus
   multi-user product, then enforce the corresponding production authorization and
   safe file ownership/versioning before exposing any dataset.
3. **P1: finish the promised main flow.** Real image upload, valid photo-parcel
   matching, reliable required-language PDF extraction and complete provenance.
4. **P1: prove results.** Correct the benchmark, validate crop/stage and trust
   behavior, and measure real costs and latency. Align all submission claims.
5. **P1: make runs durable and recoverable.** Storage, run history, review handling,
   bounded processing, operational monitoring, and backup/restore.
6. **P1: package and deploy.** Reproducible environment, deployment identity,
   automated checks, rollback, deployed smoke/load tests and acceptance checklist.
7. **P2 / explicit scope choice:** generic dynamic planning, parallel execution,
   streamed DAGs, wider crop/knowledge coverage, advanced exports and additional
   diagnostic features. If promised for judging, either implement them before
   submission or revise the claim; P2 does not mean an unmet promise is acceptable.

## Evidence locations

- Promise source: `FARMSYNC_Final_Submission.md`, sections 1, 3, 4.2 and 5;
  `FARMSYNC_IMPLEMENTED_PROPOSAL.md`, sections 2, 3, 5, 8 and 9.
- Document fabrication and limited OCR: `farmsync/documents/extractor.py`,
  `_get_easyocr_reader` and `extract_document_claims`, especially lines 516–637.
- Controlled reproduction: `scratch/document-evidence-gap.json`.
- Predefined planning: `farmsync/router/compiler.py`, template specs and `compile`.
- Assumed routing metrics: `farmsync/router/router.py`, `CapabilityRegistry`.
- Sequential executor and historical baseline assumptions: `farmsync/orchestrator.py`.
- Trust constants/proxies: `farmsync/trust/trust_score.py`.
- Crop metadata: `farmsync/vision/weights/classes.json`; training procedure:
  `farmsync/vision/train_crop_model.py`; inference: `farmsync/vision/classifier.py`.
- Corpus: `farmsync/knowledge/corpus/agronomy_corpus.json` and `advisory.py`.
- Auth, uploads, endpoint inventory and integration flags: `farmsync/server.py`.
- Report grounding: `farmsync/ai/engine.py`, `process_query`.
- CDN assets and snapshot-style UI telemetry: `farmsync/static/index.html`.
- Runtime specification: `requirements.txt`; no lockfile/deployment/CI artifacts
  found in the checked project file inventory.
- Earlier live checks: `scratch/aws-approved-check.json` and
  `scratch/aws-location-check.json`.

This turn added this assessment and the controlled probe output. It did not fix
these remaining application gaps or re-run the full regression suite. The 180-pass
result refers to the preceding regression run.
