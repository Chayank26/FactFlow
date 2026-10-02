# Direction log

Updated after every completed phase. Current milestone: Part 6 Phase 2 complete (Parts 4 and 5 complete). Current local ports: frontend 5179, API 8019.

## Part 6 Phase 2 — Local OCR extraction

Implemented the selected Tesseract/pypdfium2 path and materialized the synthetic scan corpus. Native-only pages retain pypdf extraction; image-bearing pages (including native headings with scanned content) and pages without native text use whole-page English OCR. Facts record extraction method, the UI labels OCR evidence, and documents persist/display specific failure reasons. Schema v2 upgrades existing facts to native without replacing their data. Original source PDFs remain unchanged.

Extraction runs in a disposable process with a 90-second document deadline, 20-second OCR-call deadline, 40-page limit, 300-DPI rendering, and 12M-pixel page limit. A failed OCR page rejects the new extraction and preserves earlier facts. Upload waits via the existing threadpool; no durable background jobs were added. Installed Tesseract 5.5.3 with English data, pypdfium2 5.13.0, and Pillow 12.3.0; regenerated the lockfile to include installed runtime/test dependencies and explicitly listed multipart support.

Verification: 53 backend tests, eight mocked desktop/mobile checks, real browser/API integration with scanned upload, frontend build, and whitespace checks pass. Clean, mixed-page, same-page mixed, numeric/negation, duplicate, and text-control exact gates pass. Rotated input rejects explicitly; mildly degraded input recovers expected text. Operational tests cover missing engine/language, renderer failure, timeouts, encryption, limits, and retained evidence; migration tests preserve legacy rows. One-off worker times were 0.153s clean, 0.176s rotated rejection, and 0.151s degraded, not a load benchmark. A PDFium context-manager mismatch was corrected during development. A diagnostic fixture import touched the tracked local schema; restored that file to its clean starting bytes and split pure fixture helpers to prevent recurrence. No local document changes remain in the diff.

Suggested commit message: `feat: add bounded local OCR with extraction provenance and failure reporting`

Part 6 Phase 2 is complete. Phase 3 remains: measure broader latency/resources and decide on processing progress/background execution. No git commit was created.


## Part 6 Phase 1 — OCR readiness

Part 6 has three phases: readiness/evaluation, OCR implementation, and measured processing-experience decisions. Completed the readiness checkpoint in docs/ocr-plan.md: eight fixture specifications with ground truth/outcomes, mixed-page and same-page mixed-content coverage, exact numeric/negation gates, operational failures, original-byte preservation, and latency/resource measurement requirements. Fixtures are defined, not yet generated or benchmarked.

Inspected local capabilities: no tesseract, pdftoppm, or ocrmypdf on PATH; no Pillow, pypdfium2, or pytesseract in the backend environment. Compared primary documentation for Tesseract, pypdfium2, and OCRmyPDF. Provisionally selected Tesseract CLI plus pypdfium2 rendering for explicit page-level integration; installation, version compatibility, recognition accuracy, and performance must be verified in Phase 2. No runtime dependencies or code changed.

Verification: the readiness document covers the planned fixture classes, acceptance gates, alternatives, environment gaps, and Phase 3 measurement boundary. All 37 backend tests pass from backend/ using the documented command. An initial test invocation from the repository root failed module imports; rerunning from the documented working directory passed. Markdown links/fences and whitespace checks pass. Browser/build checks were not rerun for documentation-only changes. No OCR benchmark or support claim is made.

Suggested commit message: `docs: define OCR fixtures acceptance gates and implementation plan`

Phase 1 is complete as a specification/evaluation checkpoint; Phase 2 must materialize fixtures and validate the provisional stack. Two phases remain. No git commit was created.


## Part 5 Phase 3 — Original source inspection

Added GET /documents/{id}/source to serve the registered PDF inline, with its filename and application/pdf type. Resolved paths must stay inside the configured upload directory; missing documents/files or out-of-directory paths return 404. Added a shared source link in document details, Facts, and both comparison panels, targeting a new tab with the recorded page fragment. This follows lifecycle clarity so retained evidence remains explicitly marked while users inspect the source.

Verification: 37 backend tests, eight desktop/mobile browser checks, the real browser/API workflow, frontend build, and git diff --check pass. API regressions cover exact original bytes/headers, deletion, missing files, and out-of-directory protection. Integration assertions verify links in all three views and fetch identical PDF bytes; mocked checks verify a page-two reference. PDF viewer rendering/page-jump behavior is viewer-dependent and was not asserted. Existing warnings and expected damaged-fixture parser diagnostics remain non-blocking.

Updated README with source inspection and its boundaries. No new dependency or schema change. Part 5 is complete; proposed Part 6 evaluates and introduces OCR in separate phases. No git commit was created.

Suggested commit message: `feat: link evidence to original source PDFs and pages`


## Part 5 Phase 2 — Retained evidence and count clarity

Failed reprocessing now refreshes document metadata and the selected detail view. Document evidence, Facts, and both sides of Comparisons label evidence retained from an earlier successful run when the latest extraction failed. Status-fetch failures report uncertainty; textless failed documents say no evidence is available. Successful retries clear the failed status and its warning. The backend preservation policy remains unchanged.

Facts and Comparisons summary cards now show current-filter results only in the active view, with explanatory labels. Inactive/loading/failed views show a dash; successful empty responses show zero. Document/comparison fetches now guard against aborted response/finalizer updates. This phase follows real integration setup so the failure-and-recovery lifecycle can be exercised end to end.

Verification: 34 backend tests, eight mocked desktop/mobile browser checks, the real integration workflow, frontend build, and git diff --check pass. The integration test corrupts only a temporary fixture PDF, verifies warnings in Documents/Facts/Comparisons, restores the PDF, and verifies successful reprocessing. A backend regression proves old facts survive failure and are replaced on success. Browser checks assert zero versus unavailable counts. Integration testing exposed a test-navigation race; helpers now wait for the destination heading before selecting its controls. Existing dependency/color warnings and expected parser diagnostics for the damaged fixture remain.

Suggested commit message: `fix: clarify retained evidence after failed reprocessing and scope counts`

Part 5 Phase 3 (original-source inspection and provenance) is the only remaining phase. No git commit was created.


## Part 5 Phase 1 — Real browser/API integration

Part 5 has three planned phases. Phase 1 is complete: added a separate Playwright integration configuration, real PDF workflow test, and Python backend launcher. A temporary directory is selected before app import, so even initialization cannot touch normal storage. Dedicated ports 5190/8029 and refusal to reuse servers prevent accidental tests against an existing app. Test-only CORS allows the real cross-origin browser request without changing application defaults.

The workflow uploads two generated PDFs, verifies processed status and stored files, traverses evidence beyond the first page, searches facts by source, checks a matching comparison with both filenames, reprocesses and verifies replacement fact IDs, then deletes documents and verifies empty API collections and removed PDFs. This closes the live browser/API contract gap left by the mocked suite.

Verification: the new integration workflow passed in installed Chrome (one desktop test); all 33 backend tests and the frontend build passed. Backend shutdown completed normally after the browser run. git diff --check passes. The unchanged eight-check mocked suite was not rerun in this phase. Existing dependency/color-environment warnings remain non-blocking. No new dependency or production behavior change was introduced.

Suggested commit message: `test: add isolated real browser and API integration workflow`

Two Part 5 phases remain: Phase 2 clarifies failed reprocessing/retained evidence and count freshness; Phase 3 improves original-source inspection and provenance. No git commit was created.


## Part 4 Phase 9 — Documentation reconciliation

Completed the Part 4 documentation checkpoint after the feature and browser-test phases. README now states the implemented boundaries: paginated fact responses, local extraction/status behavior, retained facts after failed reprocessing, search wildcard semantics, comparison scaling, and view-dependent summary counts. Corrected backup guidance to preserve SQLite and PDFs together while stopped, and documented absolute-path restore constraints. Added the committed browser-test files to the project map. No application code changed.

Verification: reviewed README against backend routes/extraction/storage, frontend request/state behavior, environment example, npm scripts, and Playwright configuration. All 33 backend tests pass in this phase. Documentation links/paths and git diff --check pass. Phase 8's eight browser checks and successful frontend build remain the latest results for those unchanged files; they were not rerun for this documentation-only change. Backup/restore commands were reviewed, not executed on user data. Existing backend deprecation warnings remain.

Suggested commit message: `docs: complete Part 4 documentation and outline next milestones`

Part 4 is complete. No git commit was created. Earlier phase entries remain historical snapshots; this entry and the current summaries supersede earlier planned/completed statements.

## Roadmap — current status and proposed later parts

All three Part 5 phases are complete; their checkpoints are recorded above. Remaining phases are proposed, not completed or a commitment to specific tools. Continue with one verified phase at a time, updating all three logs and providing a commit message after each checkpoint.

### Part 5 — Real integration and evidence reliability

1. **Complete:** Start an isolated backend for browser tests and run real PDF upload → extraction → evidence → comparisons → deletion. Checkpoint: repeatable full-stack workflow without touching local data.
2. **Complete:** Make failed reprocessing and retained evidence explicit in the UI, with regression coverage; clarify counts and freshness. Checkpoint: failure cannot silently present old evidence as newly processed.
3. **Complete:** Improve source inspection and provenance, including direct access to the original PDF/page. Checkpoint: users can check each displayed claim against its source.

### Part 6 — Scanned PDF support

1. **Readiness specification complete:** Define representative scanned/text/mixed fixtures and extraction acceptance criteria; evaluate local OCR options before selecting dependencies.
2. **Complete:** Add an OCR processor with page provenance and explicit failures. Checkpoint: scanned and mixed documents produce inspectable evidence without regressing text PDFs.
3. Add processing progress/background execution if measured OCR latency requires it, then verify retries and reprocessing. OCR accuracy must be reported as a limitation, not assumed.

### Part 7 — Larger collections and evaluated comparisons

1. Measure retrieval and comparison cost on a representative collection; bound document/comparison responses and reduce unnecessary pair work.
2. Build a labeled comparison evaluation set before considering semantic matching or a model. Checkpoint: measured improvements and traceable evidence, with explicit errors/limitations.
3. Reconcile operational documentation and decide whether deployment is needed. Authentication, storage portability, upload resource limits, and deployment controls belong in a separate deployment milestone if public/multi-user use is chosen.


## Part 4 Phase 8 — Browser workflow checks and polish

Added a repository-owned Playwright suite and npm test:e2e command so the core browser workflows can be rerun after changes. Four scenarios run at desktop and mobile widths: upload/document lifecycle/evidence pagination, Facts search/filter/navigation, comparison filters/evidence, and failures/recovery. The suite intercepts API calls and uses a dedicated test server on port 5189, leaving local application storage untouched. Real API/extraction/storage tests remain in pytest.

Replaced obsolete Coming soon, future-upload, Getting started, and HOW IT WILL WORK copy with descriptions of current behavior. Fixed the health indicator's fallback API port from 8018 to 8019. Upload inputs now disable while a request is active and retain their DOM reference for cleanup after the asynchronous request. Added ignored browser artifacts and documented installation, test commands, and coverage boundaries in README.

Verification: all eight browser checks pass using installed Chrome at 1280x800 and 390x844; all 33 backend tests and the frontend production build pass; git diff --check passes. The first browser run exposed a fixture issue: a one-request simulated health outage was consumed by React development-mode effect replay. Persistent failure state until explicit recovery fixed the simulation, after which the complete suite passed. Existing backend deprecation and browser-runner color-environment warnings are non-blocking.

Suggested commit message: `test: add browser workflow coverage and polish current UI`

Phase 9 documentation reconciliation remains planned. No git commit was created.


## Part 4 Phase 7 — Comparison reliability and wording

Replaced token-set equality as the agreement rule: reordered or repeated words can change a claim, even when its token set stays identical. Agreement now requires equal wording after case/whitespace normalization and removal of final sentence punctuation. Internal numbers, units, signs, word order, and repetition remain significant. Nonmatching wording requires at least two shared non-connecting terms and 50% token overlap to become a possible difference. Added a deterministic fact-ID tie-breaker to comparison ordering.

The comparison view now labels results Matching wording and Possible difference, explains the text-matching boundary, and gives accurate no-match guidance. API relationship values remain agreement/difference for compatibility. This phase follows complete pagination so users can inspect the evidence behind these tentative relationships.

Verification: all 33 backend tests and the frontend production build pass. Eleven new API regression cases exercise case/spacing normalization, reordered words, negation, quantities, units, signed values, repeated words, connecting-word-only overlap, unrelated claims, and same-document exclusion. Matching cases also verify evidence linkage, both relationship filters, source filtering, and repeat request stability. git diff --check passes. Existing dependency deprecation warnings remain; no new browser interaction suite was added in this phase.

Suggested commit message: `fix: make comparison matching conservative and clarify result labels`

Phase 8 browser checks and polish remain planned. No git commit was created.


## Part 4 Phase 6 — Complete evidence pagination

Fixed the document-detail integration left behind when Phase 4 changed GET /facts from an array to a page envelope. Details now read items and total, request 20 facts at a time, and provide Previous/Next controls and a visible range. This phase comes after test isolation so regression runs safely exercise documents with many claims.

Evidence requests cancel when the user switches or closes documents or navigates away. Failed requests display a dedicated error and retry button. Opening a document resets the offset; reprocessing refreshes its evidence and clamps an offset that exceeds the new total. The Facts browser also recovers from an out-of-range offset and ignores canceled results. Fact ordering now uses ID as the final tie-breaker after creation time and source page.

Verification: all 22 backend tests pass, including a real 65-claim PDF traversed across four pages with tied timestamps/pages, deliberately reversed insertion order, repeated requests, and an empty beyond-end page. Frontend production build and git diff --check pass. A temporary Playwright/installed Chrome check passes for four evidence pages, boundary controls, previous navigation, switching documents, error/retry, reprocess shrink recovery, and closing details; no browser exceptions. Browser checks used mocked API responses; pytest covered the real API and storage. Existing dependency deprecation warnings remain.

Suggested commit message: `fix: complete document evidence pagination and stabilize fact ordering`

Phase 7 remains planned; this checkpoint does not implement comparison changes. No git commit was created.


## Part 4 roadmap after Phase 4

Continue in small, reviewable phases. After each checkpoint passes, update direction.md, flow.md, and tech.md and provide a change summary and suggested git commit message. Later phases below remain planned, not completed.

- **Phase 5 — Isolate backend tests (complete):** prevent regression runs from writing to local application data. Checkpoint: full backend suite, frontend build, and unchanged runtime files.
- **Phase 6 — Finish pagination integration (complete):** make every document-detail fact accessible, add deterministic fact ordering, and verify navigation beyond the first result page.
- **Phase 7 — Improve comparison reliability (complete):** cover misleading token matches with regression examples and align classification and UI wording with what the heuristic can establish.
- **Phase 8 — Browser workflow checks and polish (complete):** add repeatable browser checks for upload, evidence browsing, pagination, reprocess/delete, filters, and errors; remove obsolete future-feature labels.
- **Phase 9 — Documentation reconciliation (complete):** synchronize operational guidance and current-state descriptions with verified behavior and record the next milestone. OCR remains future work with its own processor and dependency decisions.

## Part 4 Phase 5 — Isolated backend test storage

The existing suite initialized and wrote to the local application database, so test safety comes before further feature work. Added a configurable FACTFLOW_DATA_DIR with the existing backend/data default. Pytest redirects import-time initialization to temporary storage, then supplies a fresh database and upload directory for each test. Updated the schema check to read the active database path and added two independent upload checks proving fresh state and temporary file storage.

Verification: all 21 backend tests pass; the frontend production build passes. Compared SHA-256 hashes and file inventories before and after the suite: all 116 existing runtime files remained unchanged, with no additions or removals. Two existing dependency deprecation warnings remain. No git commit was created.

Suggested commit message: `test: isolate backend database and uploads per test`


## Part 4 Phase 4 — Search and pagination

Moved Facts search into the API and added validated limit/offset pagination with total-count metadata. The Facts browser now requests server-filtered pages by document and search text, displays the total count, and provides previous/next controls. Updated tests to scope generated-data searches to their own document so local runtime data cannot make assertions nondeterministic.

Verification: the full backend suite passes with 19 tests and the frontend production build passes.

## Part 4 Phase 3 — Extraction pipeline hardening

Changed extraction success to require at least one retained fact. Valid PDFs with no extractable text now receive `extraction_failed` rather than the misleading `processed` status, while their source file remains available for inspection and future OCR/reprocessing. Updated a stale test fixture to satisfy the existing minimum-signal rule.

Verification: the full backend suite passes with 17 tests and the frontend production build passes. OCR for image-only PDFs remains intentionally deferred.

## Part 4 Phase 2 — Upload and API security hardening

Hardened upload filenames by stripping Unix and Windows path components, rejecting empty or overlong names, and preserving only the controlled basename under the upload directory. Existing PDF content-type, extension, and 10 MB size validation remain active. Added focused security regression tests while preserving malformed-PDF retention for later reprocessing.

Verification: the full backend suite passes with 16 tests and the frontend production build passes. True PDF signature inspection and rate limiting remain future security work.

## Part 4 Phase 1 — Database and migration hardening

Added an explicit SQLite schema version, indexes for document/fact lookup and ordering, and a startup upgrade boundary that preserves existing local data. Added operational README guidance for backing up and resetting the ignored development database.

Verification: the schema test confirms `user_version = 1` and the fact lookup index; the full backend suite passes with 12 tests and the frontend production build passes. This is a local development migration boundary, not production database infrastructure.

## Part 3 progress checkpoint

Part 3 is focused on making the Part 2 workflow reliable and usable beyond the initial happy path. Phase 1 remains the planned fact browser and has not been marked complete here. Phase 2 is now complete: documents can be inspected, reprocessed, deleted, and validated at the API and browser boundaries.

## Part 3 Phase 2 — Document management

Added document detail retrieval, PDF-only upload validation, a 10 MB size limit, PDF reprocessing, and deletion of documents together with their extracted facts and stored files. The Documents view now provides detail, reprocess, and delete actions, and shows the document’s extracted evidence in the detail panel.

Verification: the focused backend suite passes with 5 tests covering document storage, extraction, comparisons, detail/reprocess/delete behavior, and invalid upload rejection. The frontend production build passes. The phase is paused for review.

## Part 3 Phase 3 — Extraction quality

Improved the deterministic PDF extractor so it splits sentence-level claims, filters empty and low-signal noise, and removes repeated claims case-insensitively across a document. Existing page and source-text provenance remains attached to every retained fact. Image-only PDFs remain outside this phase because they require OCR rather than text extraction.

Verification: the backend suite passes with 6 tests, including a regression test for sentence splitting, noise filtering, and deduplication. The frontend production build passes. The phase is paused for review.

## Part 3 Phase 4 — Comparison improvements

Added server-backed comparison filters for source document and relationship type, with validation for unsupported relationship values. The Comparisons view now loads available documents when opened and refetches results when either filter changes, while retaining the existing evidence-first comparison cards.

Verification: the full focused backend suite passes with 7 tests and the frontend production build passes. The phase is paused for review.

## Part 3 Phase 5 — Reliability and regression coverage

Enabled SQLite foreign-key enforcement for every database connection and added explicit regression coverage for missing-document operations, malformed PDFs, oversized uploads, and orphaned facts. The browser now reports document and comparison loading failures instead of silently rendering empty states, and aborted navigation requests do not create false errors.

Verification: the full focused backend suite passes with 11 tests and the frontend production build passes. The phase is paused for review.

## Part 3 Phase 6 — Polish and documentation

Updated the README to describe the implemented upload, extraction, document-management, and comparison workflows; added the complete backend test command and current verification guidance. Added backend/data to Git ignore rules so local SQLite and uploaded runtime files are not staged accidentally. The browser file pickers now advertise PDF-only input.

Verification: all 11 backend tests pass and the frontend production build passes. The phase is paused for review. Part 3 Phase 1, the dedicated fact-browser view, remains planned and is not being marked complete by this documentation phase.

## Part 3 Phase 1 — Dedicated facts browser

Completed the deferred Facts view with API-backed loading, document filtering, claim/evidence search, page references, source passages, loading and failure states, and a live fact count in the dashboard. This closes the remaining Part 3 Phase 1 gap identified during the later phases.

Verification: all 11 backend tests pass and the frontend production build passes. The full Part 3 feature set is now represented in the browser; OCR for image-only PDFs remains the main extraction limitation.

## Part 2 planning checkpoint

We are starting Part 2 with a phased approach so each build step stays small and reviewable. Planned phases and goals:

- Phase 6 — SQLite document records and upload API scaffolding.
- Phase 7 — Document list and metadata screen in the browser.
- Phase 8 — PDF extraction and fact storage grounded in evidence.
- Phase 9 — Comparison workflow and context-aware summary experience.

This pause is intentional: after each phase we will update the three learning logs, verify the change, and stop so the user can review the progress before continuing to the next stage.

## Phase 6 — SQLite document records and upload API

Added the first persistent layer: a SQLite-backed document table and upload/list routes in the backend. The upload endpoint writes the file to a local data/uploads directory, records filename, size, type, storage path, timestamp, and status, and exposes a GET /documents list for later UI rendering. This comes before browser document screens so storage is proven before the frontend depends on it.

Verification: the targeted backend test passes with pytest. It uploads a sample file and confirms the document appears in the list response. The endpoint is now ready for the next phase’s document display work.

## Phase 7 — Document list and metadata screen

Connected the Documents view to GET /documents and added a working PDF upload control that sends files to POST /documents. Uploaded records now appear with filename, status, file size, content type, and creation date; the Documents summary card also shows the stored count. This phase makes the Phase 6 persistence layer visible and usable in the browser.

Verification: the frontend TypeScript and Vite production build passes. The first build caught and fixed a type-only import requirement in the new upload handler. The phase is paused for review before PDF extraction begins.

## Phase 8 — PDF extraction and evidence-backed facts

Added deterministic PDF text extraction with pypdf and a SQLite facts table linked to source documents. PDF uploads are processed immediately, document status becomes `processed` when extraction succeeds, and each non-empty extracted line is stored with its document ID, page number, original source text, and creation timestamp. The `GET /facts` endpoint supports listing all facts or filtering by document.

Verification: focused backend tests pass for both the existing document upload/list flow and a generated one-page PDF. The PDF test exercises the real upload route, parser, SQLite insert, and filtered facts response. Phase 8 is paused before adding fact rendering to the frontend.

## Phase 9 — Comparison workflow and context-aware evidence

Added cross-document comparison generation from the stored facts, without duplicating comparison rows in the database. The API pairs claims from different documents, classifies exact normalized matches as agreement and materially overlapping claims as differences, and returns both source documents, claims, page numbers, and source text. The Comparisons view now loads and presents those relationships with responsive evidence panels.

Verification: the focused backend suite passes for document storage, PDF extraction, and cross-document comparison. The frontend production build also passes. Phase 9 completes the planned Part 2 workflow and is paused for review.

## Phase 1 — Project foundation
Created separate frontend and backend folders, Git ignore rules, and a persistent documentation agreement in AGENTS.md.
This comes first so browser code and Python processing have clear homes and generated files, credentials, and large reference PDFs do not enter Git accidentally. The supplied PDFs and ZIP stay on disk.
Verification: both folders and all three learning logs exist. Git initialized and this foundation committed.

## Phase 2 — React homepage
Created the React/TypeScript entry point, a small homepage, and Vite build configuration. A working browser foundation comes before API integration so frontend setup errors are isolated.
Verification: TypeScript and production build pass; Vite serves on http://127.0.0.1:5173. Downloads and localhost binding required sandbox permission.

## Phase 3 — Health API
Created the FastAPI application and typed GET /health response. A minimal endpoint proves the Python server works before introducing browser networking, storage, or PDF parsing.
Verification: live HTTP request returned 200 with {"status":"ok","service":"fact-layer-api"}. Backend runs on port 8000.

## Phase 4 — Browser/API connection
Added a health component with loading, success, offline, timeout, and retry behavior. Allowed the two exact local frontend origins in FastAPI. This verifies the network boundary before building feature screens.
Verification: production build passes; live CORS response allows the frontend origin; headless Chrome renders “Backend connected” after a real API request.

## Phase 5 — Navigable application shell
Built a responsive sidebar/top navigation, breadcrumb, page heading, reusable section metadata, and distinct Documents/Facts/Comparisons empty states. Added clear future-feature labels; upload is disabled and metrics use dashes because no database exists yet. This phase establishes where later document, fact, and relationship features will live after both runtime foundations and the API boundary have been verified.

Hash navigation preserves the section across refresh and browser Back without introducing routing infrastructure for three placeholders. Added focus indicators, a skip link, current-page semantics, live connection status, and reduced-motion handling. Reviewed desktop/mobile screenshots and removed decorative artwork on small screens to keep text clear.

A live check discovered port 5173 serving another local project. Current defaults are **frontend 5178 and backend 8018**; CORS, API config, and README were updated together. Earlier log entries retain the ports used at those checkpoints. Existing unrelated project processes were not stopped.

Verification: TypeScript/production build; real Chrome navigation across all three views; Back and reload; disabled upload; mobile navigation and no horizontal overflow at 390px; simulated failed health request followed by successful retry; no browser exceptions. Added local run instructions in README.md. Part 1 is complete; next is Phase 6, SQLite document records.
