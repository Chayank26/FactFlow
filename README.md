# Fact Layer

A practice project for extracting grounded facts from PDFs and comparing their context. **Part 9 Phase 2 is complete; Parts 4–8 are complete.** The app supports PDF upload and local storage, deterministic text extraction with evidence references, document management, a searchable fact browser, and filtered cross-document comparisons. Local English OCR supports scanned and mixed PDFs. All three Part 5 phases are complete. Later proposed parts are recorded in direction.md.

## Current capabilities and boundaries

- **Documents:** upload PDFs with a `.pdf` filename and `application/pdf` MIME type, up to 10 MB; inspect, reprocess, or delete them. Filenames are sanitized and limited to 120 characters. Extension/MIME checks do not prove valid PDF content; parsing decides whether extraction succeeds.
- **Extraction:** local `pypdf` text extraction plus Tesseract OCR for pages with raster images or no native text, followed by sentence splitting, noise filtering, and document-level deduplication. Facts retain document ID, page number, and the extracted claim as source text. This is not a full surrounding passage or an independent truth check. Each evidence item links to the stored PDF and its page in a new tab. Facts record `native` or `ocr` extraction method; OCR evidence is labeled for manual verification.
- **Status:** a stored upload becomes `processed` only when at least one fact is retained; otherwise it remains stored as `extraction_failed`. Successful reprocessing replaces facts and their IDs. Failed reprocessing marks the document failed but preserves previous facts, which remain visible with an earlier-run warning in document details, Facts, and Comparisons. Failed reprocessing refreshes the document status; a successful retry clears the warning. If status cannot be fetched, the UI reports uncertainty.
- **Facts:** server-side source filtering and SQL `LIKE` search over claim/source text. Browser pages contain 20 facts; API pages default to 50 and allow 1–100. Responses contain `items`, `total`, `limit`, and `offset`. Search uses SQL wildcard semantics (`%` and `_`), not full-text or semantic search.
- **Comparisons:** derived across documents on each request, using the heuristic described below. Documents and Comparisons are paginated. A token index avoids many unrelated comparisons; dense collections can still require quadratic work.
- **Local scope:** no accounts, authentication, background job queue, model calls, or public deployment setup. Extraction runs in a disposable process while upload/reprocess requests wait. The upload handler copies in bounded chunks and rejects files over 10 MiB, but multipart parsing/spooling occurs before this check; this is not a whole-request resource cap.

Navigation uses URL hashes; filters and selected-document state live in browser memory. Facts and Comparisons summary cards show results for current filters only in their active view. Inactive/loading/failed views show a dash, and successful empty results show zero. The Documents count is the latest loaded collection size; these are request-time snapshots, not live global metrics. Fact ordering is stable for unchanged records, but offset pages can shift when records change, and reprocessing changes IDs.

## OCR support and limits

All three Part 6 phases are complete. Synthetic OCR workloads met the declared local latency targets, so bounded request-bound processing is retained. See the [OCR plan and results](docs/ocr-plan.md).

On macOS, install the native engine before using scanned PDFs:

```sh
brew install tesseract
tesseract --list-langs
```

The language list must include `eng`. Install the Python renderer/image packages using the backend lockfile below. Tested versions: Tesseract 5.5.3, pypdfium2 5.13.0, Pillow 12.3.0. `FACTFLOW_TESSERACT` can specify an executable name or absolute path. Native text-only PDFs remain usable without Tesseract. The process-group timeout implementation targets macOS/Linux, not Windows.

Processing limits: **40 pages**, **300-DPI rendering**, **12 million pixels per rendered page**, **20 seconds per Tesseract call**, and **90 seconds per document**. These are conservative limits, not a performance guarantee or a hard total-memory quota. Upload size remains 10 MB.

Every image-bearing page is OCRed as a whole, even when it contains native text; this catches scanned content below selectable headings but can also OCR decorative images/logos and reinterpret native text. Any OCR failure rejects the whole new extraction rather than silently omitting that page. Blank/unreadable pages can therefore fail an otherwise readable document. Original PDFs and prior facts survive failed reprocessing; the UI displays a persisted failure reason.

Recognition currently targets upright English printed text. A basic word-confidence rejection gate is not an accuracy guarantee. Rotation correction, handwriting, complex layouts/tables, additional languages, and extraction history remain unsupported. The rotated fixture was rejected; clean and mildly degraded fixtures passed. Schema version 2 adds extraction method and error metadata; existing facts default to native text.

## Processing feedback and performance

Uploading/extracting and reprocessing show a persistent busy notice. Conflicting upload/reprocess/delete actions disable until completion. You can browse other sections; completion refreshes the current view without forcing navigation. Failures permit retry and preserve prior evidence.

There is no percentage progress, user cancel action, durable queue, or resume-after-reload behavior. Section navigation does not cancel processing. Reloading or closing the tab loses client state while the server may continue until completion or its deadline.

Two-trial local synthetic runs took up to 0.35s / 2.38s / 9.48s for 1 / 10 / 40 full-page scans. Largest child-process memory peaks were approximately 144–163 MiB, not total concurrent memory. These sparse repeated-page fixtures do not establish performance for every document or machine. See [measurement details and reproduction command](docs/ocr-plan.md#phase-3-results-and-decision) before interpreting these results.

## Run locally

Requirements: Node.js 22.12+ (tested with 24.18), Python 3.13 (tested with 3.13.9).

### Backend — terminal 1

```sh
cd /Users/chayankbhargava/Projects/FactFlow/backend
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8019 --reload
```

On this machine Python 3.13 is at `/opt/anaconda3/bin/python3.13`; use that full path if `python3.13` is not on PATH. The existing `.venv` is already installed, so you can skip the first two setup commands when returning to this workspace.

### Frontend — terminal 2

```sh
cd /Users/chayankbhargava/Projects/FactFlow/frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5179. API health: http://127.0.0.1:8019/health. Interactive API docs: http://127.0.0.1:8019/docs. Stop each server with Ctrl+C in its terminal.

The dedicated ports avoid another project running on 5173. Strict port mode makes a collision explicit. To use another API address, copy frontend/.env.example to frontend/.env.local, change VITE_API_BASE_URL, and restart Vite. This value is public browser configuration, never a secret. If the frontend port changes, update the allowed origins in backend/app/main.py as well.

## Verify

```sh
cd /Users/chayankbhargava/Projects/FactFlow/backend
.venv/bin/python -m pytest -q tests

cd ../frontend
npm run build
```

Then open the website with both servers running. Upload a PDF, search and filter its extracted facts, inspect a document’s evidence using its Previous/Next controls (20 facts per page), reprocess or delete it, and open Comparisons to filter relationships by source and type. Check the connected indicator, each navigation item, browser Back and refresh. Stop the backend and refresh to see the offline message; restart it and select Retry connection.

The backend suite covers upload, PDF extraction, evidence references, document lifecycle, comparison filters, and failure paths. Each test uses a fresh temporary database and upload directory; test collection also initializes storage outside the local app data directory. Running tests does not populate or modify your local document collection. The frontend build is a compile-time check. The Playwright suite below checks browser interactions with controlled API responses; it is not a live browser-to-backend integration test or a full accessibility audit.

## Browser workflow checks

From `frontend/`, after `npm ci`:

```sh
npx playwright install chromium
npm run test:e2e
```

Alternatively, use installed Google Chrome without downloading Chromium:

```sh
PLAYWRIGHT_CHANNEL=chrome npm run test:e2e
```

Playwright starts and stops its own Vite server on port **5189** (the port must be free), uses a fixed API URL for interception, and runs six scenarios at desktop and mobile widths for twelve checks. No backend server is needed: API responses are mocked, uploads use test bytes, and local documents are untouched. Backend pytest separately validates real PDF extraction and persistence.

Coverage includes upload, evidence pagination, reprocess page recovery, cancel/confirm deletion, fact search/source filters, comparison filters and evidence, browser Back/reload, failure messages, health/evidence retry, and a mobile overflow check. Failed tests retain traces under ignored `frontend/test-results/`; inspect a trace with `npx playwright show-trace <trace.zip>`. Browser exceptions fail the test. This currently checks Chromium/Chrome at two viewport sizes, not every browser or device.

## Real browser/API integration check

After installing the backend locked dependencies into `backend/.venv` and frontend dependencies/browser as above, run from `frontend/`:

```sh
npm run test:integration
# Or use installed Google Chrome:
PLAYWRIGHT_CHANNEL=chrome npm run test:integration
```

This separate suite starts a real FastAPI server on **8029** and Vite on **5190**, and refuses to reuse running servers; both ports must be free. The Python test launcher seeds and archives a temporary native/OCR collection in a separate process, makes its original path unavailable, restores it at a new root, and sets that restored data directory before importing the app and adds only the test frontend origin to its CORS middleware. Normal app configuration is unchanged. Playwright stops both servers, and graceful backend shutdown removes temporary storage. A forced process kill may leave a temporary directory behind, never the normal app database.

The test generates valid PDF bytes, then exercises browser upload, real extraction, evidence pagination, source/search filters, an agreement comparison, failed reprocessing with retained-evidence warnings across all three views, successful retry, and confirmed deletion. Direct API/filesystem assertions also verify fact replacement and removal of rows and PDFs. It uses no mocked requests. Two desktop workflows cover restored native/OCR evidence and the existing upload lifecycle; the separate twelve-check mocked suite retains broader failure/mobile coverage. Neither suite constitutes a full accessibility or production-readiness audit.

## Inspect original sources

Use **Open PDF · page N (new tab)** in document details, Facts, or either comparison source. The link requests `GET /documents/{id}/source` and passes `#page=N` to the browser's PDF viewer. The API returns the original stored bytes inline; page navigation depends on viewer support and may require manual navigation. Missing/deleted sources return 404. Source access is limited to registered files inside the configured upload directory.

The PDF is the currently stored file, not a versioned snapshot of an extraction run. Earlier-run evidence warnings still apply after failed reprocessing; replacing source bytes externally can make that evidence differ from the current file. Source links open original bytes, not a searchable OCR derivative; they do not add sentence highlighting or surrounding-passage extraction. This remains a local app without authentication.

## Collection pagination and performance

All three list APIs (`GET /documents`, `/facts`, `/comparisons`) return `{items, total, limit, offset}`. **Documents and Comparisons no longer return arrays.** Limits default to 50, allow 1–100, and the browser requests 20 per page. Documents/Comparisons offer Previous/Next controls; source filters have filename search and independent paging so every source remains reachable.

Comparison matching uses a token index while preserving the existing relationship rule. Exact totals still require examining candidate matches, and dense collections can remain expensive. See [benchmark methodology, results, and reproduction](docs/collection-performance.md). Source processing status is carried with evidence, independent of the document list page.

## Comparison limits

Comparisons show **Matching wording** when claims match after normalizing case, whitespace, and final sentence punctuation. **Possible difference** means different wording shares at least two terms after removing common connecting words and meets a token-overlap threshold. Review both source passages: neither label establishes truth or proves a contradiction, and paraphrases or unrelated contexts can be misclassified. API filter values remain `agreement` and `difference`.

## Local database maintenance

The development database defaults to `backend/data/factlayer.db` and PDFs live in `backend/data/uploads/`; runtime files are ignored by Git. The six legacy artifacts have been removed from tracking while preserving their local bytes. See the [operations runbook](docs/operations.md#repository-data-caveat). Set `FACTFLOW_DATA_DIR` before starting the backend to use an alternative storage directory. The commands below assume the default location and are run from the project root.

Stop the backend before backing up so metadata and files describe the same state. Back up the **whole data directory**, not just SQLite:

```sh
mkdir -p "$HOME/FactFlow-backups"
tar -czf "$HOME/FactFlow-backups/factflow-data-$(date +%Y%m%d-%H%M%S).tar.gz" -C backend data
```

The example keeps archives outside the repository. To restore at the same project location, stop the backend, move any existing `backend/data` aside, and extract the chosen archive with `tar -xzf <archive> -C backend`. Schema 3 stores source filenames relative to uploads; API responses still provide absolute paths. Legacy schema 0/1/2 collections must be backed up and upgraded at their original root before relocation. Same-path and relocated schema-3 recovery are verified with fresh processes and real browser/API checks; see the operations runbook for the procedure. A copied database alone does not preserve the source PDFs.

To reset local documents, facts, and uploaded files, stop the backend and remove the runtime data directory. The next backend start recreates the schema:

```sh
rm -rf backend/data
```

The API applies schema 3 and indexes transactionally when it starts. Back up the whole stopped collection before upgrading. Invalid/out-of-root, symlink, or duplicate legacy paths abort the upgrade without partial database changes; restore at the original root to resolve migration failures. Newer schemas are refused. Downgrade requires restoring a compatible pre-upgrade backup. This is a local development migration boundary, not a production backup system.

## Learning logs

- [direction.md](direction.md): why each phase's steps came at that point and how completion was verified.
- [flow.md](flow.md): user journey and data/request flow after each phase.
- [tech.md](tech.md): tool choices, alternatives, and trade-offs by phase.

AGENTS.md requires updates to all three files after every completed phase. Earlier entries remain as history; the latest entry describes current behavior.

## Structure

```text
frontend/src/App.tsx           Navigation and page shell
frontend/src/BackendStatus.tsx Health request, timeout, and retry
frontend/src/index.css         Responsive visual styling
frontend/playwright.config.js  Isolated browser test server and viewports
frontend/tests/                Mocked-API browser workflow checks
backend/app/main.py            FastAPI API, SQLite storage, extraction, and comparisons
backend/app/extraction.py      Document deadline and subprocess lifecycle
backend/app/ocr_worker.py      Native extraction, rendering, and English OCR
backend/tests/                  Backend tests and isolated browser API launcher
frontend/integration/          Real browser/API workflow
frontend/playwright.integration.config.js  Integration server lifecycle
```

Original reference PDFs and ZIP remain untouched and are ignored by Git. Runtime SQLite data and uploaded files default to backend/data and are ignored; legacy tracking has been removed while local files were preserved. No model service or credentials are needed for local development.

## Comparison quality evaluation

A reproducible evaluation covers 48 synthetic labeled evidence pairs. The selected candidate removed one false match on a 24-pair holdout, but the production threshold remains 0.5: this small authored dataset does not establish real-world accuracy. Comparisons can miss paraphrases and negation/context relationships or surface unrelated wording overlaps. See the [rubric, results, limitations, and reproduction commands](docs/comparison-quality.md) and [raw report](docs/comparison-evaluation.json). Part 7 is complete; local single-user scope is retained. See the [operations runbook and recovery checkpoint](docs/operations.md) for configuration, troubleshooting, backup/restore, and the proposed next part.

## Part 8: storage portability and recovery

All three Part 8 phases are complete: specification, implementation, and relocation/recovery verification. The [migration plan and acceptance gates](docs/storage-portability-plan.md) define portable database references while preserving API compatibility. Schema 3 now stores filename-only references and validates source access, reprocessing, and deletion through one resolver. Invalid references return 404 for source access and 409 for process/delete; metadata hides invalid paths. Failed file deletion preserves rows for retry. Recovery verification and repository hygiene are complete. Existing local data was preserved byte-for-byte and has not been migrated by this work. Runtime files remain locally available and are no longer tracked.

## Part 9: local ingestion reliability

Phases 1 and 2 are complete: bounded upload copying/cleanup and single-process mutation admission. Upload, reprocess, and delete share one slot; competing mutations return 503 with Retry-After while reads remain available. Run one API process per collection. One phase remains: browser failure/busy/retry verification and operations. See the [implementation, tests, and remaining resource limits](docs/ingestion-reliability.md).
