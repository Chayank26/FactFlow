# Technology decision log

Updated after every completed phase. Current milestone: Part 8 Phase 2 implementation complete (Parts 4–7 complete). Current local ports: frontend 5179, API 8019.





## Part 8 Phase 2 — Shared resolver and explicit SQLite transaction

No new tool or dependency was needed. Added pure app/storage.py using pathlib for filename validation and legacy preflight. Schema 3 keeps the stored_path column with relative filename semantics; response serialization supplies the current absolute path. Explicit BEGIN IMMEDIATE encompasses schema/index/path/version work, with rollback on exceptions and newer-version refusal. Tests inject failures after path conversion to verify schema rollback as well.

Retained SQLite and filesystem storage. Shared validation rejects traversal, outside references, source symlinks, and existing non-regular files; deletion attempts unlink before row removal and reports 409 on failure. A later database failure can still leave a missing file with retained metadata: no cross-resource atomicity or hostile-local-process race protection is claimed.

Verification: 83 backend tests and real browser/API PDF/OCR integration pass. Updated artificial /unused fixtures to filename references and legacy tests to valid original-root paths. Existing warnings remain. No frontend build rerun because frontend code is unchanged; browser integration verifies compatibility. No runtime data migration or untracking occurred. Phase 3 remains full relocation/recovery verification and repository hygiene.


## Part 8 Phase 1 — Portable reference design

**No new tool or dependency was needed.** Inspected existing pathlib/SQLite storage and pytest/Playwright consumers. Planned schema 3 retains stored_path as a filename-only database reference and resolves absolute API paths at response time. One validator will serve source/reprocess/delete; an explicit SQLite transaction must cover legacy schema/path/version changes and roll back failures.

Trade-offs: retaining the column avoids duplicate compatibility state; a new storage-key column would clarify naming at greater migration cost. Absolute paths prevent portable restore, while a remote store or migration framework exceeds current local requirements. No automatic old-root/basename inference: migrate legacy archives at their original path first. Filesystem deletion and SQLite cannot be made one transaction by this design; failure expectations are documented without claiming crash atomicity.

Verification: specification traced through current storage code and path-dependent tests; 61 baseline tests pass, with existing deprecation warnings. Defined but did not execute future migration/relocation fixture gates. Documentation links/fences and whitespace checks pass; no frontend rerun, code/schema changes, local-data migration, or runtime untracking. See docs/storage-portability-plan.md. Two Part 8 phases remain.


## Part 7 Phase 3 — Operational scope and recovery tools

**No new tool or dependency was needed.** Retained local FastAPI/Uvicorn, Vite, SQLite, filesystem source storage, and Tesseract. Documented configuration and process/data boundaries in docs/operations.md. A one-off Python standard-library tarfile/temporary-directory drill plus existing TestClient verified a consistent idle backup and same-path restore without touching local data.

**Decision/trade-offs:** retain loopback single-user operation. Hosting infrastructure, identity, queues, and managed storage add requirements that current usage does not establish. Absolute stored PDF paths prevent portable restore; copying only SQLite omits originals. Live backups and crash-consistent multi-resource snapshots are not implemented. The proposed next part addresses portability and tested recovery before reconsidering deployment. Corrected Git-ignore guidance: ignored new files coexist with legacy tracked runtime files; no automatic untracking or history rewrite was performed.

**Verification:** 61 backend tests pass; recovery preserves schema 2, SQLite integrity, facts and original bytes, with working reprocessing and deletion afterward. Documentation links and whitespace checks pass. No frontend rerun for this documentation-only phase; previous browser/build results are explicitly historical. Part 7 is complete; no deployment or new runtime configuration was applied.


## Part 7 Phase 2 — Dependency-free comparison evaluation

**No new tool or dependency was needed.** Retained Python JSON/argparse, pytest, FastAPI TestClient, and the existing token-postings matcher. Moved normalization/token functions into the pure comparison module and exposed an optional evaluation threshold; production still uses 0.5. The offline runner avoids importing the API and therefore avoids startup storage writes. No schema change.

**Evaluation design:** 48 authored pairs, equally sized development/holdout splits, explicit three-class rubric, source/page metadata and rationales. Threshold selection uses development macro-F1 with baseline proximity as tie-breaker. Raw output preserves per-label precision/recall/F1, confusion matrices, category counts, and individual errors. Tests check hand-calculated metrics, holdout-label independence, deterministic report reproduction, and API parity/provenance.

**Decision/trade-offs:** selected 0.6 improves holdout macro-F1 0.6931→0.7306 and review precision 73.33%→78.57%, with recall 68.75% unchanged. It passes the screening gate but only removes one false positive; retain production 0.5. These correlated synthetic examples have no independent adjudication or production prevalence, so they do not justify deployment or general accuracy claims. Embeddings/models might help paraphrases but add cost, privacy choices, dependencies, and evaluation requirements; defer until representative fresh evidence exists. See docs/comparison-quality.md.

**Verification:** 61 backend tests pass, including unchanged exhaustive-reference classification tests and all 48 corpus cases through the API. No frontend/build rerun was needed for pure backend refactoring and offline evaluation. Existing dependency deprecation warnings remain. One Part 7 phase remains: operational reconciliation and deployment scope.


## Part 7 Phase 1 — Token postings and shared pagination contracts

**No new dependency or schema migration was needed.** Used Python dictionaries/sets for token/exact-wording postings and reused FastAPI page validation, SQLite LIMIT/OFFSET/counts, and React state/fetch. A shared SourceSelect component independently pages/searches filenames rather than loading the entire source catalog. Document/comparison defaults are 50 items with maximum 100; browser requests 20.

**Optimization correctness:** precomputed tokens/normalized wording replace repeated parsing. Candidate pairs share at least two meaningful tokens or exact normalized wording, preserving single-term agreements. Ordered candidate traversal retains the previous pair IDs/orientation. Filtering precedes total/page selection; full response models are constructed only for the requested page. Exact counts and dense postings still cost quadratic time in the worst case. No cache, semantic model, cursor pagination, or search service was added.

**Contract/provenance:** GET /documents and /comparisons now return page envelopes instead of arrays; this is an explicit client-breaking change documented in README. Facts and comparison sides include source status so evidence warnings stay correct without unbounded document retrieval. Schema/persistence remains unchanged.

**Measurement:** isolated temporary SQLite benchmark compares indexed matches against the previous exhaustive reference and records bounded API timings/payload bytes. At 2,000 sparse facts, complete matching measured 1.707s versus 0.028s; dense 1,000-fact indexed matching measured 0.183s. Single-run TestClient timings omit network transport and do not measure peak memory/concurrency. Raw JSON and reproduction script are committed artifacts.

**Verification:** 56 backend tests (including reference equivalence, page coverage/validation, and source status), 12 mocked desktop/mobile checks, real PDF/OCR integration, frontend build, and whitespace checks pass. Existing dependency warnings remain. Comparison quality evaluation is Phase 2, not inferred from performance improvements.


## Part 6 Phase 3 — Evidence-based decision to retain request-bound processing

**No new tool or dependency was needed.** Used existing Pillow/pypdf fixture generation, Python subprocess/resource timing, and the extraction worker. Each benchmark scenario launches a fresh process so child peak RSS is comparable; scratch PDFs are temporary and the API is never imported. Added backend/scripts/benchmark_ocr.py and docs/ocr-benchmark.json for reproduction.

**Decision/trade-offs:** max times for 1/10/40 300-DPI pages were 0.350/2.382/9.476 seconds, below declared targets of 5/10/30 seconds. Retain current request-bound worker model rather than introduce a queue without evidence of need. Results cover sparse repeated scans on this arm64 Mac, not multi-user load or diverse layouts. Child peaks around 144–163 MiB exclude summed concurrency/API memory. Broader workloads or a durability/cancellation requirement can change this decision.

**UI/state:** React tracks the active processing document and upload state, exposes an accessible busy notice, disables conflicting mutations, and refreshes active queries with a revision counter when work settles. Navigation remains independent. This avoids stale active results and the prior upload-completion view/hash mismatch. Existing API timeouts provide failure bounds, but no cancellation endpoint, job persistence, percent progress, or restart recovery is claimed.

**Verification:** 53 backend tests, 10 desktop/mobile mocked tests, real scanned-PDF integration, frontend build, and whitespace checks pass. Held-response browser tests validate navigation, disabled actions, failure/retry, and refreshed results on success. Existing dependency warnings remain. Full benchmark methodology, raw values, limits, and reproduction command are recorded in docs/ocr-plan.md.


## Part 6 Phase 2 — Tesseract, PDFium, and isolated extraction

**Introduced tools:** Tesseract 5.5.3 (Homebrew, eng/osd data), pypdfium2 5.13.0, and Pillow 12.3.0. Tesseract remains an external executable; Python rendering/image versions are locked. Full environment freeze also records previously installed test/multipart dependencies missing from the old lockfile. Added python-multipart to direct runtime requirements. Primary tool references remain in docs/ocr-plan.md.

**Isolation:** pypdf parsing, PDFium rendering, and Tesseract invocation run in a disposable process rather than concurrent PDFium calls in web threads. A parent-created temporary directory is cleaned after completion; the outer deadline terminates the process group. Native-only pages do not require the renderer or OCR engine. Upload delegates the blocking wait to a threadpool so the async event loop is not blocked by the worker. This is request-bound processing, not durable background execution.

**Safety/quality trade-offs:** 40 pages, 12M pixels at 300 DPI, 20 seconds per OCR call, and 90 seconds per document are conservative bounds, not a hard memory quota or SLA. Entire image-bearing pages use OCR to avoid ignoring a scanned body below a heading. This can reinterpret native text or reject benign graphics. TSV word scores reject empty/low-score output (minimum 40, mean 80); they are heuristics, not calibrated accuracy or truth confidence. English upright print only; no rotation correction or table structure preservation.

**Persistence/UI:** dependency-free SQLite migration v2 adds extraction_method and extraction_error. Existing rows default to native. New facts are committed only after full processing succeeds; failure retains prior evidence. Labels propagate into comparison responses without changing relationship semantics. The original file is never rewritten. No OCRmyPDF/cloud provider/queue was introduced.

**Verification:** 53 backend tests (including migration and synthetic OCR gates), eight browser mocks, real scanned-upload integration, frontend build, and whitespace checks pass. Synthetic fixtures use Pillow's bundled font and pure PDF helpers; no app import or personal files are needed to generate them. Observed small-fixture worker times are recorded in the OCR plan; broader performance/memory tests remain Phase 3. Tests may skip engine-dependent gates on machines without Tesseract; this run had no skips.


## Part 6 Phase 1 — Provisional OCR architecture

No new tool or dependency was installed. Used existing filesystem/virtual-environment inspection, pytest, and primary vendor/project documentation to define the next implementation. The environment lacks Tesseract, Poppler's pdftoppm, OCRmyPDF, Pillow, pypdfium2, and pytesseract in the checked PATH/venv locations.

Provisional direction: Tesseract CLI with pypdfium2 page rendering, retaining pypdf and the existing fact pipeline. Tesseract expects images, so rendering is a separate requirement. OCRmyPDF is a broader PDF-processing alternative; a hosted service would change local-only data handling and add credentials/cost. References, trade-offs, fixture specifications, and acceptance gates are in docs/ocr-plan.md. No accuracy/performance comparison was executed; Phase 2 must verify dependency compatibility and real OCR results before locking versions.

No queue is selected. Phase 3 first measures latency/resource behavior against an explicit interactive budget and adds background execution only if warranted. Original-source preservation, page provenance, per-page limits/timeouts, and explicit incomplete-extraction behavior are required implementation decisions.

Verification: 37 backend tests pass using the documented backend working directory. Documentation links/fences and whitespace checks pass; no frontend rerun for this documentation-only phase. The first root-directory test invocation failed imports, then the documented invocation passed. Existing deprecation warnings remain.


## Part 5 Phase 3 — PDF response and shared source links

**No new tool or dependency was needed.** FastAPI/Starlette FileResponse serves PDFs inline; a small React SourceLink component reuses the existing document ID/page provenance in all evidence views. Native PDF viewers avoid adding an embedded renderer and its maintenance cost. The trade-off is viewer-dependent page-fragment behavior and no sentence-level highlighting.

**File boundary:** resolve the registered path, require containment in UPLOADS_DIR and an existing file, then serve application/pdf with inline content disposition and nosniff. Client input chooses a document ID, not a filesystem path. This is appropriate for the current local app, not a new authentication system. Missing/deleted files return 404. The response serves current stored bytes; versioned provenance and relocation of absolute stored paths remain outside this phase.

**Verification:** 37 backend tests pass, including byte/header checks, missing/deleted sources, and an out-of-directory record. Eight mocked browser checks and the real integration pass, verifying source links on all evidence surfaces and actual PDF byte retrieval. Frontend build and whitespace checks pass. Page-two URL generation is covered; native PDF rendering/page navigation is not asserted. Existing dependency warnings and deliberate malformed-PDF diagnostics remain.


## Part 5 Phase 2 — Lifecycle presentation without new persistence

**No new tool or dependency was needed.** Reused React state, fetch/AbortController, existing document status and fact endpoints, pytest, and Playwright. The backend keeps previous facts on extraction failure and replaces them only after successful extraction; this behavior now has a focused backend regression and user-facing explanation.

**Status handling:** a failed reprocess triggers metadata refresh. Existing per-view document lists provide status for fact/comparison evidence without adding status fields to every API response. Loading/missing status is explicit. This avoids a schema/API migration, but status is a snapshot and can change externally until the next fetch. Full processing history or evidence-generation timestamps are not introduced.

**Count semantics:** active-view filtered counts avoid presenting cached values as global totals without adding an expensive global comparison-count endpoint. Unknown/loading/failed/inactive counts use a dash, successful empty results use zero. Aborted document/comparison response and finalizer guards prevent obsolete requests from replacing active state.

**Verification:** 34 backend tests, eight mocked desktop/mobile checks, one real browser/API lifecycle test, frontend build, and whitespace checks pass. Real integration covers temporary PDF corruption, retained evidence warnings, restored bytes, and successful retry; mocked tests check zero/unavailable semantics. Navigation helpers wait for the destination heading before acting to avoid selecting the previous view's similarly named controls. Expected parser diagnostics during deliberate corruption are not application exceptions.


## Part 5 Phase 1 — Isolated full-stack browser test

**No new tool or dependency was needed.** Reused Playwright, installed Chrome, Python tempfile, Uvicorn, FastAPI CORS middleware, and the existing FACTFLOW_DATA_DIR setting. The separate integration config keeps real-server tests distinct from deterministic mocked browser tests.

**Isolation/lifecycle:** the launcher creates TemporaryDirectory before importing app.main, overriding inherited storage settings so import-time initialization is isolated. Playwright owns both server processes, disallows reuse, and sends SIGTERM for graceful backend shutdown. The temporary context then cleans its database/uploads. Forced process termination can bypass cleanup. Ports 5190/8029 and a test-only origin isolate the run without broadening normal application CORS.

**Coverage choices:** a single serial desktop workflow exercises real browser requests, CORS, valid PDF parsing, persistence, and cleanup. Additional direct API/filesystem assertions check facts are replaced during reprocessing and deleted with PDFs. Generated ASCII PDFs use proper stream lengths/xref offsets and avoid committing binary fixtures. Mocked mobile/failure tests remain valuable but cannot replace this real contract check. This workflow is not broad OCR/layout/production coverage.

**Verification:** one installed-Chrome integration test, 33 backend tests, frontend build, and whitespace checks pass. The backend shutdown log confirms normal exit. No production code, schema, or dependency changed; Phase 2/3 will address lifecycle presentation and source inspection.


## Part 4 Phase 9 — Documentation and next technical decisions

**No new tool or dependency was needed.** Retained Markdown and repository inspection for documentation, plus the existing pytest suite for backend verification. React/TypeScript/Vite, FastAPI/Pydantic, SQLite, pypdf, and Playwright remain the current stack. README setup uses the existing lockfiles and records app ports 5179/8019 and browser test port 5189.

**Documented trade-offs:** synchronous extraction and full upload reads are simple locally but do not establish bounded-memory/background processing. SQLite LIKE is adequate for current search but has wildcard semantics and no full-text index. Derived comparisons avoid stale persisted pairs but enumerate quadratically. Current source text is the extracted claim. Failed reprocessing preserves earlier evidence; absolute stored PDF paths limit storage portability. These are explicit current limitations, not fixes introduced by documentation.

**Backup boundary:** a SQLite-only copy omits original PDFs. README now documents stopping the backend and archiving the whole data directory outside the repository, plus same-location restore assumptions. Backup commands were not executed on user data; production backup/recovery infrastructure remains out of scope.

**Proposed next decisions:** Part 5 should reuse Playwright/pytest with an isolated real backend to prove the frontend/API contract and improve provenance. Part 6 should evaluate OCR against representative fixtures before choosing native binaries or services. Part 7 should measure scale and comparison quality before adding indexing, candidate matching, embeddings, or a model. No OCR engine, AI provider, queue, deployment platform, or further dependency has been selected or installed.

**Verification:** documentation audited against code/configuration, 33 backend tests pass, local links/paths and whitespace checks pass. The latest frontend build and eight browser checks are the Phase 8 results for unchanged application/test files; no new frontend verification run is claimed. Existing backend deprecation warnings remain.


## Part 4 Phase 8 — Browser workflow checks and polish

**New development tool:** @playwright/test is now a locked frontend dev dependency with a committed config and workflow suite. Real-browser assertions exercise event handling, navigation, layout, requests, and error recovery that the TypeScript build cannot verify. Component-only tests would be lighter but would not cover the assembled browser workflow. No runtime dependency or database schema was introduced.

**Deterministic isolation:** Playwright intercepts the fixed test API URL and supplies per-test response state. The test server uses port 5189, refuses to reuse another server, and overrides VITE_API_BASE_URL so local configuration cannot silently redirect tests. The browser suite does not prove the live frontend/backend contract or PDF parsing; existing isolated pytest tests cover the real backend. A full integration environment would require isolated backend startup and fixtures and remains a separate extension.

**Browser choice:** default runs use Playwright Chromium; PLAYWRIGHT_CHANNEL=chrome supports installed Google Chrome. Verification used installed Chrome at desktop and mobile viewport sizes, not device emulation or multiple engines. Retained traces aid failures and are Git-ignored. The simulated outage remains active until explicit recovery, accommodating React StrictMode's development effect replay without weakening assertions.

**Retained tools and fixes:** React/fetch, native file inputs, existing CSS, FastAPI, SQLite, and pytest remain. The health fallback now matches port 8019. Upload inputs disable while busy and retain their element reference for asynchronous reset. Static UI wording now describes available functionality.

**Verification:** eight browser checks, 33 backend tests, frontend build, and whitespace checks pass. Existing dependency deprecation and runner color-environment warnings remain non-blocking. README records commands, browser installation, isolation, and scope.


## Part 4 Phase 7 — Comparison reliability and wording

**No new tool or dependency was needed.** Retained Python string/regex operations, SQLite, FastAPI, React, and pytest. Agreement compares case-folded, whitespace-normalized strings with final sentence punctuation removed, preserving internal symbols, word order, and repetition. This replaces set equality, which cannot distinguish reversed subjects/objects or repeated words.

**Candidate matching trade-off:** a small English connecting-word exclusion set reduces generic-word matches. Different wording must share at least two remaining tokens and meet the existing 0.5 overlap threshold. Regex tokens support Unicode words; numbers participate in candidate matching, while their exact formatting/signs remain significant for agreement. This is a conservative heuristic, not semantic analysis: it can miss paraphrases and short related claims or still match unrelated contexts. The thresholds are not an evaluated accuracy guarantee, and the exclusion list is not multilingual language processing. Embeddings or an LLM would require a separate evaluation dataset, provenance decisions, and dependency/cost assessment.

**Compatibility and presentation:** API values remain agreement/difference; user-facing labels are Matching wording/Possible difference. Summaries explain the matching basis without claiming verified truth or contradiction. A unique fact-ID ordering tie-breaker makes pair orientation stable for unchanged records; reprocessing still replaces fact IDs. Comparisons still use quadratic pair enumeration and remain unpaginated; this phase makes no scale claim.

**Verification:** 33 backend tests pass, including 11 new parameterized/API cases, and the frontend build passes. Tests exercise real PDF upload/extraction and comparison responses with per-test temporary storage. UI changes are text-only and compile-checked; repeatable browser coverage remains Phase 8. Existing dependency deprecation warnings remain.


## Part 4 Phase 6 — Complete evidence pagination

**Retained application tools:** React state/effects, fetch with AbortController, the existing FastAPI page envelope, SQLite, and pytest were sufficient. No new runtime dependency or schema migration was needed. Document details reuse the existing fact-pagination CSS and API rather than loading every fact into browser memory.

**Stable ordering:** added the unique fact ID as the last SQL sort key after created_at DESC and source_page ASC. This resolves ties common to extraction batches without changing the schema. ID ordering is deterministic for existing records, not semantic sentence order, and reprocessing generates new IDs. Cursor/snapshot pagination could address concurrent dataset changes but would add an API contract change beyond this local phase; offset pages can still shift when data changes.

**Request lifecycle:** effect cleanup cancels obsolete detail requests; aborted results and finalizers cannot overwrite the active request state. A separate evidence error state keeps failures distinct from empty documents and supports retry. Both evidence and Facts offsets clamp to the last valid page when results shrink.

**Verification tool:** temporarily installed Playwright under /tmp and used installed Chrome for a targeted browser smoke check. This adds no project dependency or lockfile change. Controlled API responses make page navigation, failure/retry, and reprocessing shrink behavior deterministic; real extraction/storage is exercised separately by pytest. A committed repeatable browser suite remains Phase 8 work.

**Verification:** 22 backend tests pass, frontend production build passes, and browser checks pass without exceptions. The 65-fact backend test explicitly reverses insertion order to verify the tie-breaker rather than relying on SQLite's incidental row order. Existing dependency deprecation warnings remain.


## Part 4 Phase 5 — Isolated backend test storage

**No new tool or dependency was needed.** Retained pytest, FastAPI TestClient, SQLite, and the Python standard library. The autouse pytest fixture uses tmp_path and monkeypatch to create fresh storage for every test, including existing tests without changing each call site.

**Import-time isolation:** app.main currently initializes SQLite when imported. A fixture alone would run too late to prevent that initialization from touching local data, so conftest sets FACTFLOW_DATA_DIR to a TemporaryDirectory before collection imports the app. The backend reads that optional setting and retains backend/data as the default. The prior environment value is restored at pytest shutdown.

**Trade-offs:** real temporary SQLite files exercise actual schema, foreign keys, uploads, and extraction more faithfully than database mocks or a shared in-memory connection. An application factory or lifespan-based initialization could eliminate import-time side effects more broadly, but would expand this phase unnecessarily. Tests reference the module's current DB_PATH rather than a copied path that would outlive monkeypatch changes. Pytest may retain recent per-test temporary directories for debugging; these are outside local application storage.

**Verification:** 21 backend tests pass, including two independent fresh-state upload cases. Frontend production build passes. All 116 local runtime file hashes and the inventory remained unchanged. Existing Starlette/httpx and AnyIO deprecation warnings remain non-blocking.

**Next decisions (planned):** reuse the current API and React stack for Phase 6 pagination; evaluate comparison behavior against examples in Phase 7; select browser-check tooling in Phase 8. OCR tooling is deferred to a separate milestone.


## Part 4 Phase 4 — Search and pagination

**Bounded API response:** the Facts endpoint validates `limit` from 1 to 100 and `offset` from zero, returning an envelope with items, total, limit, and offset. This keeps the browser payload bounded and leaves room for a future full-text index.

**SQL search:** the current implementation uses case-insensitive `LIKE` conditions over claim and source text. This is adequate for the local dataset and avoids introducing a search engine before usage patterns justify one.

**Deterministic tests:** because the ignored SQLite database persists across test runs, generated-data tests scope queries by their newly created document ID. This prevents unrelated local fixtures from changing expected totals.

**Verification:** 19 backend tests and the frontend production build pass. Existing Starlette/httpx deprecation warnings remain non-blocking.

## Part 4 Phase 3 — Extraction pipeline hardening

**Success criterion:** parser completion is not enough to claim processing success. `extract_facts` now requires at least one retained fact after sentence splitting, quality filtering, and deduplication. This makes the document status reflect usable output rather than only the absence of a parser exception.

**Failure preservation:** textless PDFs remain stored with `extraction_failed`, matching the existing malformed-PDF behavior and allowing a future reprocess/OCR path without requiring another upload.

**OCR boundary:** no OCR dependency or external service was added. OCR has different native binaries, runtime cost, and deployment requirements, so it should be introduced as a separate processor with its own tests and status model.

**Verification:** 17 backend tests and the frontend production build pass. Existing Starlette/httpx deprecation warnings remain non-blocking.

## Part 4 Phase 2 — Upload and API security hardening

**Basename sanitization:** replacing backslashes before splitting on `/` handles both common path separator styles. The stored name is limited to the final component and a bounded length, preventing submitted paths from influencing file placement.

**Validation layering:** extension and declared MIME type are checked before persistence, while the existing parser determines whether a correctly identified PDF is processable. This preserves useful `extraction_failed` records without treating the client-declared MIME type as proof of valid PDF bytes.

**Deferred security work:** byte-signature validation, rate limiting, authentication, and deployment-level request limits are not introduced in this local single-user phase.

**Verification:** 16 backend tests and the frontend production build pass. Existing Starlette/httpx deprecation warnings remain non-blocking.

## Part 4 Phase 1 — Database and migration hardening

**SQLite `user_version`:** the built-in schema version marker provides a dependency-free migration boundary appropriate for this local application. Startup applies the current version and indexes without replacing existing data. A dedicated migration framework can be introduced if the schema gains multiple deployed versions or rollback requirements.

**Indexes:** document creation ordering and fact lookup/order are indexed because those paths back the current list, detail, and comparison workflows. Indexes use `IF NOT EXISTS` so startup is repeatable.

**Operational guidance:** the README now documents a simple file backup and a deliberate local reset. This is transparent for a practice project, but it is not a substitute for production backups, migrations, or deployment tooling.

**Verification:** 12 backend tests and the frontend production build pass. Existing Starlette/httpx deprecation warnings remain non-blocking.

## Part 3 Phase 6 — Polish and documentation

**README as operational documentation:** the setup and verification guide now describes the actual current system rather than the original shell milestone. It includes backend tests, frontend build verification, API URLs, and the main manual workflow.

**Runtime-data hygiene:** backend/data is ignored because SQLite and uploaded files are local runtime state. This prevents test fixtures and personal source documents from entering commits while leaving the data directory available during development.

**Native PDF hint:** the file input uses `accept="application/pdf,.pdf"` to improve picker guidance. Server-side validation remains authoritative, so this browser hint does not replace the API boundary.

**Verification:** the complete backend suite passes with 11 tests and the frontend production build passes. No new runtime dependency was introduced.

## Part 3 Phase 1 — Dedicated facts browser

**Shared endpoint contract:** the browser reuses `GET /facts` and its existing optional document filter rather than creating a second facts API. This keeps source selection authoritative on the server and avoids duplicating document relationships in the client.

**Local search:** claim and source-text search happens in the browser because the current fact set is small and the interaction should feel immediate. Full-text indexing belongs in a later scale-focused phase.

**Evidence presentation:** each card keeps the extracted claim paired with its page number and source text, preserving the evidence-first design established in Part 2.

**Verification:** all 11 backend tests and the frontend production build pass. No new dependency was needed.

## Part 3 Phase 5 — Reliability and regression coverage

**SQLite foreign keys:** SQLite does not enforce foreign keys unless enabled per connection, so `PRAGMA foreign_keys = ON` is now applied both during initialization and whenever a connection is opened. This protects the document/fact relationship across all API operations.

**Visible load errors:** empty results and failed requests have different meanings. The frontend keeps dedicated error state for Documents and Comparisons and ignores expected aborts, preventing misleading empty screens during outages or navigation.

**Regression scope:** the backend suite now covers 11 focused behaviors across extraction quality, document lifecycle, comparison filters, and reliability failures. Existing Starlette/httpx deprecation warnings remain non-blocking.

## Part 3 Phase 4 — Comparison improvements

**Server-side filtering:** document and relationship filters are query parameters on the existing comparisons endpoint. Filtering before response construction keeps the browser payload smaller and ensures all clients receive the same relationship semantics.

**Validated relationship values:** the API accepts only agreement and difference. Returning a 400 for unsupported values makes client mistakes visible and prevents silent empty states from being misread as “no comparisons.”

**Native selects:** the UI uses accessible native select controls because the filter sets are small and stable. A heavier combobox would add interaction complexity without improving this workflow yet.

**Verification:** 7 backend tests and the frontend production build pass. Existing Starlette/httpx deprecation warnings remain non-blocking.

## Part 3 Phase 3 — Extraction quality

**Sentence splitting:** a small regular-expression boundary keeps the extractor dependency-free while turning parser lines containing multiple claims into separate facts. It is intentionally conservative and handles common terminal punctuation rather than attempting full natural-language parsing.

**Quality filter:** claims must contain at least three alphanumeric words and five alphabetic characters. This removes separators and empty extraction artifacts without pretending to judge the truth or importance of a claim.

**Document-level deduplication:** case-folded claim strings provide an explainable exact duplicate check. Semantic duplicates remain available for later matching in the comparison layer rather than being discarded here.

**Verification:** 6 backend tests and the frontend production build pass. OCR was not added because scanned-PDF support is a separate capability with different runtime and dependency trade-offs.

## Part 3 Phase 2 — Document management

**Server-side validation:** the upload endpoint now requires a PDF filename and `application/pdf` content type, and enforces a 10 MB limit. Client-side `accept` hints can improve the picker experience, but they are not a security boundary, so validation remains in FastAPI.

**Explicit cleanup:** deletion removes facts, the document row, and the stored file in one application workflow. The database currently uses explicit dependent-row cleanup rather than relying on a migration to alter the existing facts foreign key.

**Reprocessing:** extraction is shared by initial upload and the process endpoint. Reprocessing replaces the document’s prior facts, which avoids duplicate evidence while keeping the document ID stable for future links.

**Verification:** 5 focused backend tests and the frontend production build pass. The suite emits existing Starlette/httpx deprecation warnings, but no test failures.

## Part 2 planning checkpoint

Part 2 keeps the same architecture but introduces the first persistent layer. The planned stages use the tools already present in the stack and defer additional complexity until the data model is proven:

- SQLite for local document metadata and extracted fact records.
- FastAPI endpoints for upload, listing, and retrieval operations.
- React state and fetch calls for document interactions in the browser.
- PDF parsing only when the storage model is stable enough to support evidence linkage.

This staged sequence keeps each change testable and leaves room for a later switch to a richer OCR or extraction pipeline if the project grows.

## Phase 6 — SQLite document records and upload API

**SQLite:** a lightweight embedded database fits this project’s local-first workflow and keeps setup simple. It is enough for document metadata and later extracted fact records without adding another service or running a separate database container. The trade-off is that the local database file becomes part of the app state and should be treated as development data, not shared production infrastructure.

**FastAPI File uploads:** using UploadFile and multipart form parsing keeps the API aligned with browser uploads. This is a good fit for PDF intake and allows the app to validate file type and size at the route boundary before storing content. A more elaborate upload layer would be useful later, but this is enough for the current document persistence step.

**Data directory layout:** storing uploaded files in backend/data/uploads while SQLite keeps metadata in backend/data/factlayer.db keeps the persistence layer easy to inspect and easy to delete during development. The included PDFs and other reference materials remain outside the database and are not automatically imported.

**Verification:** the upload/list test passes in the project venv with pytest, proving the route writes a file and records it in SQLite. This is the foundation for the next phase’s document list UI.

## Phase 7 — Document list and metadata screen

**React fetch and local state:** the Documents screen uses the existing fetch-based approach rather than adding a data-fetching library. The small number of records and one upload action do not yet justify caching or global state. An AbortController prevents a stale list request from updating the component after navigation.

**Multipart browser upload:** a native file input and FormData send the selected file without manually setting the Content-Type header. The browser supplies the multipart boundary, while the FastAPI UploadFile route receives the file and persists it.

**Metadata presentation:** the UI formats byte counts and ISO timestamps at the display boundary, leaving API values structured and stable for later filtering or document detail views. The status is displayed as returned by the backend rather than inferred in the browser.

**Verification:** the frontend production build passes after correcting the new type-only React import. No PDF extraction library was added in this phase; the next phase will introduce it only alongside evidence storage.

## Phase 8 — PDF extraction and evidence-backed facts

**pypdf:** a focused, local PDF parser is sufficient for text-based reference PDFs and avoids adding a model or external service before the evidence schema is established. Scanned PDFs will need OCR in a later phase because text extraction alone cannot recover image-only text.

**Line-based fact records:** the first extractor preserves each non-empty PDF text line as a fact and uses the page number plus source text as its evidence reference. This is deliberately conservative: it avoids inventing claims or silently discarding provenance while giving the next UI phase concrete records to display. More semantic claim segmentation can be introduced after real documents reveal its requirements.

**SQLite relationship:** facts store the parent document ID rather than duplicating document metadata. The API supports an optional document filter so the frontend can load a focused evidence set without adding a separate query layer.

**Verification:** the focused backend suite passes with 2 tests. It covers document upload/list behavior and a real generated PDF upload through extraction, persistence, and filtered retrieval. The lock file records the installed pypdf version for repeatable setup.

## Phase 9 — Comparison workflow and context-aware evidence

**Derived comparisons:** comparison relationships are computed from facts at read time instead of stored in another table. This keeps the first version simple and prevents comparison data from becoming stale when source facts are reprocessed. A persisted comparison model can be introduced later if ranking, review state, or user annotations require it.

**Token overlap heuristic:** normalized token sets provide an explainable baseline for finding same-subject claims without an LLM. Exact token-set matches represent agreement; at least half shared tokens with remaining differences represent a difference. The heuristic is intentionally conservative and should be replaced or augmented with semantic matching when the project has enough real examples to evaluate it.

**Evidence-first UI:** each comparison renders both claims and source text with page numbers and filenames. The interface reports the relationship as derived context rather than presenting a conclusion without the underlying passages.

**Verification:** the focused backend suite passes with 3 tests, including a real two-document comparison, and the frontend production build passes. This completes the planned Part 2 phases.

## Phase 1 — Project foundation
**One Git repository with frontend/ and backend/:** one history keeps application changes and learning notes together. Separate repositories would add coordination overhead for this solo practice project. A monorepo orchestrator would add machinery before we have shared packages or complex build dependencies.
**Git:** local checkpoints make each phase inspectable and reversible. Manual folder backups do not provide useful diffs or coherent history. No hosted service is required to run locally.
**Markdown:** these logs are readable in the IDE and versioned alongside code. An external notes application would separate explanations from the changes they describe.

## Phase 2 — React, TypeScript, Vite
**React:** component composition will let the document list, evidence panel, and comparison views share UI patterns. Vue and Svelte are valid alternatives; React matches the agreed learning stack and avoids switching ecosystems during this project. The trade-off is explicit state/effect handling and more boilerplate than some alternatives.
**TypeScript:** catches inconsistent props and API shapes during development; plain JavaScript has less setup but fewer static checks. Types do not replace runtime validation.
**Vite:** provides a focused client dev server and production build. Next.js adds server-rendering conventions we do not currently need with our separate Python API. A manual Webpack setup adds configuration work. The installed dependency graph is recorded in package-lock.json.
Reference: https://vite.dev/guide/

## Phase 3 — Python API
**Python 3.13 + venv:** a project-local environment isolates dependencies from other projects. The machine default is Python 3.9, so this setup explicitly uses the installed 3.13 interpreter. A Conda environment could work but is unnecessary for this small web service.
**FastAPI:** typed request/response handling and generated /docs suit the future extraction API. Flask is smaller but requires more choices for validation and API documentation. Django includes useful full-site features, such as its ORM and admin, which this phase does not need. Express would keep one language across the app but move processing away from the planned Python PDF tooling.
**Pydantic:** validates and serializes the health response and will later validate claims. Plain dictionaries are simpler but do not enforce the response contract.
**Uvicorn:** serves the ASGI application locally; its reload mode aids development. A production process manager is premature here.
**requirements.lock.txt:** records exact installed versions for repeatable setup; requirements.txt expresses direct dependencies. Regenerate the lock after intentional dependency changes.

## Phase 4 — Fetch, effects, and CORS
**Browser fetch + AbortController:** enough for one GET with cancellation and timeout. Axios adds a dependency without a current need for interceptors. A query library becomes useful when we have cached document/fact lists; local component state is adequate now.
**React effect:** ties the connection check to mounting and retry, with cleanup to prevent stale updates. No global state library is needed for one isolated status component.
**FastAPI CORSMiddleware:** browsers treat ports 5173 and 8000 as different origins. Explicit local origins let the browser read the response. A wildcard is unnecessary; CORS is not authentication. A Vite proxy is an alternative but would hide the cross-origin boundary we want to learn here. GET is the only allowed method for now; extend this deliberately when uploads arrive.
**VITE_API_BASE_URL:** makes the API location configurable without editing components. Vite embeds this value in public browser code, so it must never contain secrets.
**Temporary Playwright + installed Chrome:** verifies actual browser fetch/CORS behavior that curl alone cannot prove. Kept outside application dependencies because this is a small smoke check.
Reference: https://fastapi.tiangolo.com/tutorial/cors/

## Phase 5 — Layout and navigation
**Tailwind CSS via its Vite plugin:** integrates the agreed styling stack and provides a shared baseline plus utilities for later components. This shell mostly uses named CSS classes so a learner can inspect layout rules together in one stylesheet. Plain CSS alone would be enough for this phase; Tailwind is a consistency choice, not a runtime requirement for facts. Bootstrap would provide more preset components but impose a visual style; CSS-in-JS would add component styling machinery we do not need.

**Lucide React:** named SVG icon imports give the navigation and evidence concepts a consistent visual vocabulary. Hand-drawn icons take maintenance time; emoji have inconsistent appearance and semantics across platforms. Icons accompanying text are decorative and the text supplies the label.

**Native hash links + React state:** support direct section URLs, Back/Forward, refresh, and keyboard navigation for three views. React Router becomes worthwhile with nested document detail URLs, route loading, or more complex navigation. A state-only switch would lose URL/history behavior. No Redux or global store is justified at this scale.

**CSS flex/grid and media queries:** adapt the same document structure to desktop and mobile. Separate mobile pages would duplicate state and markup. System fonts avoid external font requests. Decorative document artwork uses CSS and SVG icons; raster image generation is unnecessary for these simple shapes.

**Dedicated ports 5178/8018 and strict frontend port:** avoid a discovered conflict with another project. Silently choosing a new frontend port could break the explicit CORS origins, so a collision should be visible. CORS still allows only the two intended local frontend origins.

**Retained tools:** React, TypeScript, Vite, FastAPI, Pydantic, fetch, local component state, and Git remain appropriate. No database, PDF parser, LLM, or authentication tool was added in Part 1 because no implemented task requires them yet.

Reference: https://tailwindcss.com/docs/installation/using-vite
