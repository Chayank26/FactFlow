# Direction log

Updated after every completed phase. Current milestone: Part 4 complete through Phase 9. Current local ports: frontend 5179, API 8019.

## Part 4 Phase 9 — Documentation reconciliation

Completed the Part 4 documentation checkpoint after the feature and browser-test phases. README now states the implemented boundaries: paginated fact responses, local extraction/status behavior, retained facts after failed reprocessing, search wildcard semantics, comparison scaling, and view-dependent summary counts. Corrected backup guidance to preserve SQLite and PDFs together while stopped, and documented absolute-path restore constraints. Added the committed browser-test files to the project map. No application code changed.

Verification: reviewed README against backend routes/extraction/storage, frontend request/state behavior, environment example, npm scripts, and Playwright configuration. All 33 backend tests pass in this phase. Documentation links/paths and git diff --check pass. Phase 8's eight browser checks and successful frontend build remain the latest results for those unchanged files; they were not rerun for this documentation-only change. Backup/restore commands were reviewed, not executed on user data. Existing backend deprecation warnings remain.

Suggested commit message: `docs: complete Part 4 documentation and outline next milestones`

Part 4 is complete. No git commit was created. Earlier phase entries remain historical snapshots; this entry and the current summaries supersede earlier planned/completed statements.

## Proposed upcoming parts — not implemented

These are a proposed sequence, not additional completed phases or a commitment to specific tools. Continue with one verified phase at a time, updating all three logs and providing a commit message after each checkpoint.

### Part 5 — Real integration and evidence reliability

1. Start an isolated backend for browser tests and run real PDF upload → extraction → evidence → comparisons → deletion. Checkpoint: repeatable full-stack workflow without touching local data.
2. Make failed reprocessing and retained evidence explicit in the UI, with regression coverage; clarify counts and freshness. Checkpoint: failure cannot silently present old evidence as newly processed.
3. Improve source inspection and provenance, including direct access to the original PDF/page. Checkpoint: users can check each displayed claim against its source.

### Part 6 — Scanned PDF support

1. Define representative scanned/text/mixed fixtures and extraction acceptance criteria; evaluate local OCR options before selecting dependencies.
2. Add an OCR processor with page provenance and explicit failures. Checkpoint: scanned and mixed documents produce inspectable evidence without regressing text PDFs.
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
