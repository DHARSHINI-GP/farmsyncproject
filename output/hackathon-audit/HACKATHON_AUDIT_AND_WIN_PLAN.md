# FARMSYNC hackathon audit and one-day delivery plan

Audit date: 18 October 2026, Asia/Kolkata. Target deadline: 19 October 2026.

## Decision

The project has a useful working prototype, but **all original promises are not implemented or verified**. It cannot honestly be certified as perfectly working or production-ready. Passing tests establish their covered behavior, not general crop accuracy, legal ownership, source authenticity, live cloud availability or a winning probability.

The best deadline strategy is to correct credibility gaps, prepare reproducible demonstrations, and add one tightly scoped differentiator: an **Evidence Recovery Copilot** with a small adversarial evaluation workbench. This is a recommendation/specification, not an already implemented feature.

## Evidence gathered in this audit

- Full offline regression: **226 passed, one skipped module**, one Starlette/httpx deprecation warning; 220.61 seconds. Command: `python -m pytest -q --tb=short`, with offline models and one CPU thread configured.
- Separately enabled the already installed `scratch/test-deps` dependency directory: **six cloud adapter tests passed using Moto mocks**. This resolves the skipped cloud test module for local adapter coverage; it does not prove an AWS deployment.
- Source preflight: Python syntax, direct dependency pinning and deployment artifact presence passed.
- CSS rebuild and navigation JavaScript syntax passed.
- Isolated development browser audit at localhost:8019: 396 rows loaded, the checked row moved from Survey 384 to Survey 381, compact navigation opened the actual telemetry panel, notifications opened/closed, a model could be selected, and no browser console errors were captured in the checked flow.
- Actual browser query: `Check a 100 m waterbody buffer for Survey 384`. Result: requested threshold 100 m; clearance 6941.08 m; GIS area 10.349 acres; **VERIFIED_ACCEPT**, scoped to the supplied GIS layers and configured rule. Timings and a completion notification were rendered. The score is not a legal clearance or ownership certificate.
- Live Bedrock diagnostic, outside the restricted network: STS returned **ExpiredToken**. The four model checks correctly remained NOT_RUN. Current model availability is therefore unverified.
- User-approved live Amazon Location diagnostic: geocoding returned **AccessDeniedException**; routing returned **ExpiredTokenException**. These are current diagnostic results, not proof of the precise IAM cause. Renew the assigned session and inspect the permitted resource configuration before retrying.
- Shipped crop model SHA256 matches MODEL_EVALUATION.json. That stored evaluation reports 593 held-out images, crop accuracy **89.88%**, stage accuracy **80.44%**, and no group/content overlap under its split protocol. This audit checked the artifact match; it did not retrain or independently reproduce that evaluation. Cassava, Marigold and Groundnut have zero test support.

The browser server used a separate audit database and an explicit localhost origin. It was configured offline, so that UI check is not evidence of live Bedrock model invocation.

## Promise-to-implementation audit

| Promise | Current finding | Status / judging implication |
|---|---|---|
| Text, PDF and field-image ingestion | Present; immutable owned assets, validation and selection have tests. | Working within tested formats and limits. |
| GIS parcel identity, area, buffers and subdivisions | Implemented with stable IDs and GeoPandas/Shapely in UTM 44N; tested and one buffer flow exercised in browser. | Strong, demonstrable capability; map data quality remains an input assumption. |
| OCR and land-document extraction | Source-only text/table extraction and optional English/Tamil OCR paths exist. | Partial: broad real scanned/Tamil accuracy is not independently established. |
| Real registered-owner verification | Local JSON demonstration fixtures only. | Not provided. Clearly disclose; a generated demo PDF cannot establish ownership. |
| Independent crop/stage model | Trained MobileNetV3 model and calibration artifacts exist. | Supported on evaluated supplied data; rare/absent classes and real field generalization remain gaps. No validated disease diagnosis. |
| Photo-to-parcel verification | Polygon containment exists; user-supplied location is a claim rather than independent provenance. | Working conservative policy; supplied Survey 384 photos do not establish this parcel crop. |
| Multi-model AI | Local vision, approved 3B/8B Bedrock paths and optional embeddings exist. User model selection reaches per-request calls without changing the shared default. | Implemented; current live access blocked by expired credentials. Bedrock's report call selects a constrained focus; verified prose is rendered from tools. |
| Generic agentic planning | Typed workflow DAGs plus optional constrained Bedrock planner. | Partial: dynamic planner is off by default in current configuration; execution remains sequential. Do not claim an arbitrary autonomous agent. |
| Adaptive verified-utility routing | Route scoring and escalation are implemented. | Partial: quality/risk/cost profiles are largely configured assumptions, not a learned or independently benchmarked optimum. |
| Trust and abstention | Heuristic FTS, source checks, typed results and task-specific abstention. | Working policy, not a calibrated probability. Avoid saying 0.653 means 65.3% chance of truth. |
| Source-grounded agronomy | Ten-entry corpus with crop/stage matching and retrieval exists. | Critical source-quality gap: current coconut citation misidentifies CPCRI Bulletin 98. Retrieval from a local entry is not verification of that entry's publication or dosage. |
| Evidence graph and live visual DAG | Structured nodes/edges and task progress exist; browser shows execution text/timings. | Partial: main web app does not provide the promised interactive claim/source graph or graphical live DAG. Streamlit tables are not equivalent. |
| Batch discrepancy workflow | Separate Workspace batch comparison is implemented. | Present with tested contracts; not a universal arbitrary-PDF extraction guarantee. |
| History, accounts, review, cancellation and backup | Local persistence, source access control, jobs, human review and backup/restore have tests. | Local behavior supported; cloud production recovery/rollback not certified. |
| Model choice, navigation and notifications | Recently wired UI, session notifications and persisted browser model preference. | Checked paths work. Notifications are session-local, not a persistent cross-device notification service. |
| Baseline accuracy/cost advantage | Historical 50-query results are explicitly invalidated; competitor runners simulate behavior. | Unproven. Do not claim 100% accuracy, zero hallucinations, >50% real savings or a measured win over GPT/Claude. |
| Fully deployed AWS production service | Adapters/build assets exist. Last documented deployment stopped at S3 permission gates. | Not certified; no verified public URL or current authenticated deployed acceptance was established. |

Earlier proposal/slides also name GPT, Claude, Gemini, Qwen, PostGIS, SQL and production readiness inconsistently with the current approved implementation. Rewrite the judge-facing materials around what actually runs; adding a historical disclaimer to an old overclaim does not make it a good final submission.

## Bugs fixed during this audit

1. Moved the Router Telemetry target from the GIS summary card to the actual execution trace/timing card.
2. Added a compact view selector when the desktop navigation is hidden below its width breakpoint. It stays synchronized with desktop selection.

The screenshot `browser-telemetry-notifications.png` records the actual completed browser flow. No model, trust threshold or evidence rule was weakened to obtain ACCEPT.

## What FarmwiseAI actually asks for

### Explicit in supplied organizer documents

The Dataset & Resource Access Guide says Task 1 has no separate dataset. Participants must select relevant resources from Tasks 2-6 and demonstrate multimodal, multi-model and agentic processing, retrieval, integration and validation. Independent engineering and validation are expected. Provided and independently sourced/generated data must be distinguished, and restricted data/credentials must not be exposed.

The Task 4 resource note explicitly warns that supplied ground-truth points can contain errors. It expects cleaning/validation and a developed model or deployable inference workflow rather than manual forwarding of every image to Gemini. This supports FARMSYNC's trained local crop model and conservative spatial matching; it does not require completing every Task 4 disease feature as a Task 1 submission.

The AWS guide permits the assigned core serverless services and category-specific approved models, requires Mumbai, resource prefixes and the existing execution role, and forbids permission/region bypasses. It is an access guide, not the evaluation rubric.

The guide explicitly defers evaluation criteria to the original Challenge Brief and Task 1 problem statement. Neither was found in the supplied ZIP. **Exact judging weights, mandatory integrations and deliverable format remain unconfirmed.** Task 2's terrain/raster notes should not automatically be turned into mandatory Task 1 requirements.

### Product-fit inference, not a claimed judging rubric

FarmwiseAI's public site emphasizes operational geospatial intelligence combining field, spatial and remote-sensing data for agriculture, land and governance. A defensible interpretation is that a repeatable decision workflow, source quality and actionable uncertainty are more useful differentiators than another generic chatbot or a cosmetic model picker.

Official company site: https://www.farmwiseai.com/

## Critical citation finding

The application cites `ICAR-CPCRI Technical Bulletin No. 98: Coconut Palm Management, pp. 18-24.`

The official CPCRI Bulletin 98 is titled **Community based extension mechanisms for pest and disease management of coconut - Success stories** (September 2016). Its contents do not identify a publication called Coconut Palm Management. The app's title attribution is therefore wrong. This does not by itself establish which individual nutrient amounts are wrong; those require their own source checks.

Primary source: https://cpcri.gov.in/filemgr/webfs/publication/tb98_.pdf

Before judging, replace the affected advisory with a verified source excerpt plus source URL/version and precise page/section. Remove unsupported recommendations; do not merely relabel the same unchecked recipe as verified. Validate every advisory actually used in the demo. Rebuild/recheck retrieval if corpus text changes.

## Recommended differentiator: Evidence Recovery Copilot

### User-visible result

Replace an unexplained overall abstention with a claim-level panel:

- GIS area: supported by the selected polygon and metric calculation.
- Document extent: matches the extracted source row within the configured tolerance.
- Ownership: demonstration match only; authoritative verification unavailable.
- Photo classification: image prediction available.
- Parcel crop: unresolved because photo provenance/location is not established.
- Advisory: available only when the publication and requested crop/stage are supported.

For each unresolved claim, show the reason, source, supported next action and external dependency. Example: `Verify parcel crop -> obtain a genuine parcel-linked field photo -> upload/inspect evidence -> rerun audit`. A photo from another survey or a user-entered coordinate must not be promoted to verified provenance.

### Bounded agentic loop

`Inspect evidence -> identify missing claim requirements -> propose a permitted action -> user adds evidence or requests recheck -> execute existing tools -> compare old/new run -> update claim states.`

Use deterministic requirement/action rules and validated tool contracts. Bedrock can explain the chosen action or choose among an allowlisted action set; it must not invent authoritative connectors, change a score directly or authorize external operations. Implement one real cycle with existing uploads, PDF parsing, GIS checks and durable audit history rather than claiming an open-ended autonomous agent.

### Included judging workbench

Provide a small curated challenge set with independently specified outcomes: missing owner; missing extent units; wrong village; absent subdivision; mismatched PDF extent; unrelated photo; missing photo; unavailable cloud; supported GIS-only buffer; waterbody conflict; corrupt upload; valid demo match with ownership still unverified.

Show actual results, reasons, run IDs, measured latency and token counts where returned. Count false accepted claims and unsupported assertions. Distinguish hand-authored test fixtures from organizer documents. Do not select cases based on their favorable result or label a curated test set an independent field trial.

### Why this is the right one-day scope

- Builds on the existing evidence JSON, tools, jobs and histories.
- Solves the real user problem observed repeatedly: what evidence is needed next?
- Demonstrates multimodality, failure recovery, explicit state and verification without external government access.
- Produces a clear before/after judging demonstration and measurable robustness outcomes.
- Does not depend on a new dataset, model training run, public deployment permission or expensive service.

This is product differentiation for this prototype, **not a defensible claim of worldwide research novelty**. Related work already covers verifiable agricultural agents and contract-driven tool orchestration:

- AgriWorld: https://arxiv.org/abs/2602.15325
- AgriAgent: https://arxiv.org/abs/2601.08308

## Scope comparison

| Candidate | Estimated effort after prerequisites | Tomorrow risk | Recommendation |
|---|---|---|---|
| Claim-level recovery panel plus a small challenge workbench | 7-10 engineering hours plus 3-4 validation/demo hours | Manageable if existing tools are reused and unsupported external actions remain explicit | Primary addition. |
| Verified advisory sources and clickable excerpts | 2-4 hours for the demonstrated crop/stage subset | Low to medium; full corpus may take longer | Required credibility repair, not optional novelty. |
| Measured 3B/8B comparison on the same requests | 2-3 hours plus live access | Depends on renewed credentials and permitted spend | Optional after the main flow passes; show measured tokens/time, not invented prices. |
| New satellite time series / terrain/raster pipeline | At least a separate acquisition/integration/validation effort | High by tomorrow | Defer. |
| Live government title verification | Depends on legitimate authoritative access and schema agreements | External blocker | Do not promise. |
| New disease model / large retraining / extra cloud providers | Dataset, access and evaluation requirements unknown | High | Defer. |

Effort estimates are planning estimates, not guarantees. No action can guarantee hackathon selection or perfect operation.

## Delivery sequence through tomorrow

1. **First 2-3 hours: repair the submission story.** Refresh AWS sessions; retest approved services. Correct the demo advisory citation/content. Get the original Task 1 brief/rubric. Prepare an accurate current feature sheet and remove historical performance/model claims from final slides.
2. **Next 4-5 hours: recovery workflow.** Implement claim-status schema, reasons and allowlisted next actions; wire upload/recheck/history comparison. Preserve original runs and source hashes.
3. **Next 2-3 hours: challenge workbench.** Add 10-12 clearly labelled cases and a results summary. Measure correctness against case expectations rather than comparing to simulated commercial models.
4. **Next 3-4 hours: hardening and rehearsal.** Regression tests, small and desktop viewports, corrupt inputs, missing cloud, same-survey/different-village records, two-account isolation, restart/history, cancellation and export. Rehearse the exact judging path and prepare a screen recording/offline fallback.
5. **Final scope freeze:** fix defects only. If time is short, ship the claim panel and one successful recovery loop; cut optional model comparison and visual polish first.

Reserve time for integration defects; do not spend the entire remaining window adding features.

## Definition of done for the new scope

- Every displayed claim has an evidence source or an explicit unresolved status/reason.
- Next actions refer to real UI/API capabilities; unavailable authoritative access is identified as external.
- New evidence creates a new immutable run; old decisions remain inspectable.
- A user can complete one supported recovery step and see the actual resulting claim change.
- No action fabricates ownership, relinks an unrelated photo, changes trust thresholds to force ACCEPT, or turns a hypothetical into verified evidence.
- Curated negative cases do not produce unsupported positive claims; failures are retained in the evaluation output.
- Local regression, browser flows and failure paths pass. Live/cloud results are identified separately.
- Presentation promises match the tested artifact. Crop confidence and FTS are not conflated.

## Suggested four-minute judging demonstration

1. Real GIS-only query on Survey 384: a scoped positive answer with exact 100 m threshold and executed tool timings.
2. Add a clearly marked demonstration PDF and an unrelated crop photo: show the matching extent, successful image classification and unresolved parcel/ownership claims.
3. Use Recovery Copilot to inspect the missing evidence and complete one legitimate supported recheck/recovery step; show the new run and unchanged historical evidence.
4. Run selected adversarial cases, explain one abstention and show measured outcomes. End with the reusable orchestration design and honest deployment/data boundaries.

Never present the generated Survey 384 summary as an organizer-issued notice. Its data came from demonstration registry fields, so matching that summary back to the same registry is not independent corroboration.

## Source inventory

- Organizer PDFs: data/FAI_Product_Challange/FAI_Task_Details_Requirements.pdf; FarmwiseAI_TCE_AWS_Access_Guide.pdf; TASK_2/Task_Guide/Task_2.pdf; TASK_4/Task_Guide/Task_4.pdf.
- Promises: FARMSYNC_Final_Submission.md; FARMSYNC_Proposal_Final.md; FARMSYNC_IMPLEMENTED_PROPOSAL.md; README.md; MANUAL_ACCEPTANCE.md.
- Implementation: farmsync/orchestrator.py; router/compiler.py; router/planner.py; router/router.py; documents/evidence.py; knowledge/advisory.py; trust/trust_score.py; trust/evidence_graph.py; runtime.py; cloud/; static/.
- Evaluation and operations: MODEL_EVALUATION.json; scripts/preflight.py; ORGANIZER_DEPLOYMENT_BLOCKER.md; scratch/aws-private-deployment.log; current test outputs; output/hackathon-audit/verification-summary.json; output/hackathon-audit/aws-live-check.json; scratch/location-live-check.json.

Older audit/readiness reports contain historical findings. Current code, current tests and explicitly dated live diagnostics take precedence; this report does not interpret a prior successful model call as proof of present access.
