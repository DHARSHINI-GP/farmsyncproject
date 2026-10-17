# FARMSYNC manual acceptance checklist

Use the FastAPI/Leaflet interface. Streamlit remains a local secondary demo and
does not replace the authenticated production workspace. Save the run JSON when
checking results; it contains source references, hashes, tool traces and limits.

| Function | Manual check and expected behavior |
|---|---|
| Map and parcel identity | See 396 polygons across seven villages. Select two records with the same survey number; stable parcel IDs must select their own geometry/area. A survey number alone must not resolve an ambiguous record. |
| Search and layers | Search by survey, toggle parcels/roads/waterbodies, switch imagery, zoom and fit the selected polygon. |
| GIS area and buffers | Verify an exact feature, inspect area and distances in UTM 44N. Ask for a 100 m buffer; its reported threshold must be 100 m. Missing geometry must remain unverified. |
| Subdivisions | Select a supplied FMB subdivision such as 1/3B. A nonexistent subdivision must not borrow its parent parcel's boundary. |
| PDF upload | Upload a real unencrypted PDF. Invalid, empty, encrypted, over-page-limit and oversized files must be rejected. Upload the same filename twice; each version must have a different immutable asset reference. |
| Source-only extraction | Upload a labelled row with survey/area but no owner. Owner must remain missing. Remove the area or its unit; extent must remain unknown and comparison unresolved. It must not copy a demonstration owner or polygon area. |
| Scanned documents | With provisioned OCR enabled, test a clear scan covering multiple pages. Inspect actual page references and raw snippets. Poor/ambiguous OCR must not become invented legal evidence. Tamil OCR is enabled, but independent Tamil accuracy is not established. |
| Batch comparison | Upload/select a PDF, open Workspace and run document comparison. Every identified source row appears. Ambiguous parcels and conflicting villages remain unresolved; ownership stays unverified. |
| Real photo upload/capture | Open Workspace, upload a JPEG/PNG/WebP or use capture on a supporting mobile browser. It becomes a selectable owned photo. Coordinates are an optional supplied claim, not proof of authenticity. |
| Image-only analysis | Select a photo explicitly and run crop/stage analysis. Without a verified parcel link, the result must say image-only/unverified association. Survey 384's unrelated supplied photos must not establish its crop. |
| Model limits | Inspect crop/stage predictions, confidence/escalation and class support. Unsupported/poorly represented cases require escalation/abstention. Health/disease diagnosis must remain unsupported. |
| Corpus advice | Advice must cite an actual supplied corpus entry. An uncovered crop/stage must say guidance unavailable; the corpus citations are not independently authenticated publications. |
| Ownership | Demo-registry matches may be shown as demo matches. Official ownership must always remain unverified with the supplied source set. |
| Planning and progress | Submit a query, see actual task progress, chosen tools, latency and estimated costs. With the approved dynamic planner enabled, plans use only validated capabilities; invalid model plans fall back safely. |
| Cancellation | Cancel an active run. The current bounded call returns before cancellation takes effect. Reopen history to inspect its persisted final status. |
| Saved audits | Close/reopen the workspace and restart the service. Completed runs and evidence hashes remain. Open a result and download JSON/source evidence. |
| Accounts and isolation | Create admin/user/reviewer accounts through the operator command. Sign in as two users; one user's assets, jobs and exports must be inaccessible to the other. Once accounts exist, loopback must not bypass sign-in. |
| Human review | A reviewer opens a review case, inspects its evidence and records a decision. A normal user cannot resolve cases. The original model/source result remains available. |
| AWS status | Use live checks with a valid assigned identity. Configured/untested, disabled, expired and failed access must not appear as verified connections. No AWS secret-entry modal should be present. |
| Routing | With the assigned Location identity, request geocoding and a route. Confirm the provider. When unavailable, the UI must identify its local estimate, not claim a live road route. |
| Capacity | Submit beyond the configured analysis allowance. Expect a controlled 429 and usable history, rather than uncontrolled concurrent inference. |
| Backup/recovery | Local operator: back up and restore into a new directory, verify files/results, sign in again. Cloud recovery requires its separate live restore exercise. |

Local supplied-data evaluation: 2,915 unique images; 1,860 training, 462 validation,
593 test. Crop accuracy **89.88%**, stage accuracy **80.44%**. Group/content overlap
between splits was zero under the supplied grouping metadata. This is not an
independent field trial; rare classes/stages have few or zero test examples.

Public acceptance additionally requires the AWS deployment gates in
[AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md). Passing this checklist cannot establish
100% accuracy or error-free operation for every real-world input.
