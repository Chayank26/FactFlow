# Part 9 — Local ingestion reliability

All three Part 9 phases are complete. Local single-user scope continues.

1. **Bounded upload storage (complete):** remove the handler's full-file copy, enforce the existing file-size limit while copying, and clean up handled storage/registration failures.
2. **Extraction admission and mutation coordination (complete):** bound concurrent extraction within the supported single API process; define retryable busy responses and prevent conflicting reprocess/delete operations. Verify slot release after failure and keep reads available. This is not a durable queue or multi-process lock.
3. **Failure/retry verification and operations (complete):** exercise busy/failure/retry flows through browser/API tests, verify resource-release behavior, and reconcile operating guidance. No automatic retries that could duplicate uploads.

## Implemented Phase 1 flow

FastAPI receives/parses the multipart upload → existing filename/type checks → copy at most 64 KiB per read into a temporary file inside uploads → enforce 10 MiB (the UI calls this 10 MB) → close the complete file → replace the generated destination path → insert/commit its document row → run existing extraction.

The helper reads at most the configured limit plus one byte before rejecting an oversized upload with 413. No partial or oversized source is published. Temporary copy files are removed on normal failure or task cancellation. A handled SQLite registration failure removes the published file; storage/registration failures return 500 with retry guidance. Successful registration followed by extraction failure still retains the original file and an extraction_failed record, preserving the established behavior.

File bytes and reported size remain exact; schema 3, source paths, API shape, and evidence semantics are unchanged. The browser continues to use its existing error/retry behavior.

## Boundaries

This bounds the **handler's copy**, not the entire HTTP request. Installed Starlette code parses multipart before the endpoint and uses SpooledTemporaryFile for file parts. Oversized content may already consume temporary disk space before the endpoint rejects it. No pre-parser request-body cap, reverse proxy, or public-ingress guarantee is added here.

Small file writes and SQLite work still happen synchronously within the handler. No throughput improvement or hard total-memory quota is claimed. Extraction remains request-bound with its existing document deadline. Phase 2 now admits one mutation at a time per API process; multiple processes are not coordinated.

Temporary cleanup and compensating source deletion assume the filesystem permits unlink. Process kill/power loss can leave temporary files or an unregistered source between file publication and database commit; this phase adds neither fsync-based durability nor a crash-recovery sweeper. Do not remove `.upload-*.tmp` files while the API is running. Stop it and inspect/back up storage before any manual cleanup. An upload whose response is lost may already be committed; inspect Documents before retrying. No idempotency key was introduced.

## Verification

98 backend tests pass. New tests assert bounded read requests and exact bytes at zero/one/exact-limit sizes; a helper-level zero-byte copy is not a claim of successful PDF extraction. Oversized input stops at limit+1 without files/rows. Read errors, task cancellation, partial write failure, and publication failure clean temporary files. Database connection and commit failure leave no document/source; retry succeeds with exact original bytes. The first assertions were corrected to distinguish the shared test database directory from the dedicated copy directory.

Both real browser/API workflows pass, including restored native/OCR evidence and upload/reprocess/delete lifecycle. No frontend code, dependency, schema, local data, or Git tracking changed. Existing dependency/color warnings remain. Frontend build and mocked browser suite were not rerun because the client is unchanged.

From backend, run `.venv/bin/python -m pytest -q tests`; focused checks are in `tests/test_upload_storage.py`. Use the README integration command for real browser coverage. All tests use temporary storage.

## Tools and alternatives

No new tool or dependency: UploadFile reads, tempfile, os.replace, SQLite, pytest and the existing Playwright suite suffice. A same-directory temporary file supports complete-file publication without storing the full upload as one bytes object. A raw streaming/multipart replacement or proxy-level request cap would address an earlier boundary but changes ingress behavior and needs separate testing. A queue is deferred until durability or concurrency requirements justify it.

## Phase 2 — Single-process mutation admission

Upload, reprocess, and delete share one non-blocking threading lock. A competing mutation receives HTTP 503 with `Retry-After: 1` and a message asking the caller to retry after the active operation finishes. The header is a retry hint, not a one-second completion guarantee. No operation is queued or automatically retried. All documents share the slot, so even an unrelated deletion waits for extraction to finish by retrying later.

An upload reserves the slot at endpoint entry, before validation/copy/registration, and holds it through extraction and response-model construction. Multipart parsing occurs before endpoint admission and remains outside this bound. Busy requests create no application source files or document rows; framework multipart temporary storage may already exist. While busy, mutation endpoints return 503 even for IDs that would otherwise be missing/invalid. When idle, normal 404/409/validation behavior remains.

Reprocess/delete hold the lock in their synchronous worker thread through completion. Upload copying releases the slot on normal failure or task cancellation. Once upload extraction starts, a strongly referenced, shielded task owns the slot until its worker finishes, including error handling and metadata retrieval. Cancelling the requesting task does not release the running worker's slot early. Unexpected worker exceptions are observed even when the requester has left. This does not add cancellation of the extraction worker or durable restart recovery.

Read endpoints do not acquire the mutation lock. They can return request-time snapshots, including an uploaded document whose facts have not yet been committed; no consistent multi-request snapshot is implied. Existing retained-evidence behavior is unchanged.

**Operating scope:** run one API process against a collection. Do not run multiple Uvicorn workers or separate API instances against the same data directory and expect this in-memory gate to coordinate them. Do not reload code or maintain storage during active extraction. Process shutdown/reload is not a durable handoff protocol. Direct internal helper calls, external filesystem writers, and other processes are outside admission control.

**Verification:** 105 backend tests and both real PDF/OCR browser/API regression workflows pass. Event-controlled threaded tests hold upload/process/delete in flight, assert competitors receive 503/Retry-After without extra files/rows, check health/documents/facts/comparisons/source reads, and verify successful retry afterward. Failure tests cover expected extraction failure and unexpected worker exceptions. Cancellation tests prove ownership lasts through worker completion, while cancellation during copying releases admission. Earlier copy/storage/migration/recovery tests still pass.

At the Phase 2 checkpoint there was no frontend change; dedicated busy copy and browser contention verification were deferred to Phase 3 (now complete below). No dependency, schema, or local-data mutation was made. This phase's integration runs verify existing workflow regressions, not browser contention. Build/mock tests were not rerun for unchanged frontend code. Existing warnings remain.

## Phase 3 — Browser busy handling and verified manual retry

The browser now distinguishes a 503 busy response from a failed extraction. Upload says the upload was not started and asks the user to select the file again after the active operation finishes. Reprocess says the request did not change evidence; Delete says the document was not deleted. No automatic retry, countdown, or queued job is implied. Upload errors have alert semantics; management errors retain their existing alerts. Other failure handling and retained-evidence refresh remain unchanged.

The mocked suite verifies all three busy messages at desktop/mobile widths, existing evidence, unlocked controls, explicit retries and mutation request counts. The real API/browser suite starts an actual reprocess from a second API client while a test-only wrapper holds its worker. It checks 503/Retry-After, unchanged facts/source bytes and document count, available fact browsing, then releases the worker and retries through the browser. These controls live only in backend/tests and are installed by the disposable integration launcher, never by normal app startup. The pause has a 30-second fail-safe; cleanup releases it in finally. Existing OCR/recovery and failure workflows also pass.

Checkpoint: **105 backend tests, 14 desktop/mobile mocked checks, three real browser/API workflows, and production build pass.** Backend cancellation/resource-release regressions from Phase 2 remain passing. An old unscoped alert assertion was narrowed to the intended list error after uploads gained alert semantics. Existing dependency/color warnings remain; no dependency/schema/local-data change or commit.

Part 9 is complete. Outstanding boundaries are pre-parser upload resource limits, process-crash recovery/idempotency, multi-process coordination and public deployment—not unfinished phases of this part. Use one API process per collection. A received busy response means that attempt was rejected; a lost response is ambiguous and must not be treated as a confirmed rejection.
