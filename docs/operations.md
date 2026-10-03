# Local operations and deployment decision

Updated for Part 9 Phase 1, 2026-10-03; the Part 7 recovery drill below is historical.

## Scope decision

Retain local, single-user operation on loopback. The current user workflow does not require public hosting or multiple users. Part 7 is complete; this decision does not provision or publish anything. Reconsider when remote access, multiple users, durable processing, or measured collection/concurrency demands become requirements.

A shared deployment would need a separate milestone covering authentication and per-user authorization (including source PDFs), portable storage paths, upload limits before buffering, bounded concurrent extraction, deployment configuration and secrets, TLS, recovery, and operational monitoring. CORS is not authentication. Current tests and synthetic benchmarks do not certify multi-user capacity or public deployment readiness.

## Start, stop, and configuration

Use the dependency setup and two terminal commands in [README](../README.md#run-locally). Start the API on `127.0.0.1:8019` and Vite on `127.0.0.1:5179`; both `localhost:5179` and `127.0.0.1:5179` are allowed browser origins. Keep these loopback bindings for this scope. Vite rejects an occupied development port.

| Setting | Current behavior |
| --- | --- |
| `FACTFLOW_DATA_DIR` | Read at API import/startup; defaults to `backend/data`, resolved to an absolute path. Set before starting the API. |
| `FACTFLOW_TESSERACT` | OCR executable name or absolute path; default `tesseract`. Requires English language data. |
| `VITE_API_BASE_URL` | Public browser configuration; defaults to `http://127.0.0.1:8019`. Restart Vite after editing `.env.local`; rebuild compiled assets after changing build configuration. |
| Schema | SQLite version 3, transactionally upgraded on startup; back up before upgrade; no downgrade tooling. |

For a fresh collection outside the repository, run from `backend/` with a new directory:

```sh
FACTFLOW_DATA_DIR="$HOME/FactFlow-local-data" .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8019
```

This selects a separate collection; it does not migrate existing documents. Relative data paths resolve against the process working directory, so prefer absolute paths. The usual `--reload` development server can restart during edits; avoid code edits during extraction. Stop each server with Ctrl+C. Let active extraction settle before maintenance; browser closure does not cancel server work and no durable job resumes after restart.

`GET /health` confirms the API process responds. It does not check database integrity, disk capacity, or OCR availability. Validate storage by loading Documents; validate OCR with a known scanned PDF and inspect its evidence. Check `tesseract --list-langs` for `eng` when diagnosing OCR setup.

## Backup and recovery

Stop the API and wait for active extraction to finish before copying data. Copy the entire configured data directory, including SQLite and uploads. For the default location, from the repository root:

```sh
mkdir -p "$HOME/FactFlow-backups"
tar -czf "$HOME/FactFlow-backups/factflow-data-$(date +%Y%m%d-%H%M%S).tar.gz" -C backend data
```

For custom storage, substitute its parent directory and directory name. Keep archives outside the repository; they contain original documents and extracted content. No automated schedule, encryption, retention policy, or off-machine replication is implemented.

Restore a trusted archive with the API stopped. Move the existing data directory to a dated recovery location first, then extract the backup into the original parent directory (`tar -xzf <archive> -C backend` for the default example). For legacy schema 0/1/2, preserve the original absolute root during upgrade. Schema 3 stores filenames relative to uploads; complete-directory relocation is verified for the local workflow. Startup refuses invalid/duplicate/out-of-root legacy references and rolls back all database edits. Restore the original layout rather than guessing paths. Starting with an empty directory is not migration. To roll back an upgrade, restore the whole pre-upgrade backup with compatible application code.

Before resuming work, check SQLite integrity and schema, then confirm Documents/Facts and an original PDF. On a disposable copy restored at its original path, also verify reprocessing and deletion; those mutate records. Successful reprocessing replaces fact IDs. Do not assume copying only the database recovers PDFs. Do not reset a collection without a verified backup.

**Verified recovery checkpoint:** an isolated temporary collection was uploaded, archived while idle, moved aside, and restored to its original absolute path. SQLite integrity returned `ok`, schema remained 2, facts and original PDF bytes matched, and subsequent `/documents/{id}/process` and deletion succeeded. This tests local same-path recovery, not relocation, crash consistency, live backups, or external archival durability. The live local collection was untouched.

## Repository data caveat

The six legacy runtime artifacts (database and five sample text uploads) have been removed from Git tracking with `git rm --cached`; their local files remain byte-for-byte unchanged and ignored. The files are no longer tracked; history was not rewritten. `git ls-files backend/data` now returns nothing. Do not force-add runtime files. This cleanup does not migrate the local database or remove old content from earlier commits.


## Troubleshooting and limits

| Symptom | Check/action |
| --- | --- |
| Browser offline or fetch failure | Confirm API 8019, browser API URL, and exact allowed frontend origin; restart configuration changes. Preview port 4173 is not in default CORS origins. |
| Port already in use | Stop your own prior server or consistently change client/API/CORS ports; do not stop unrelated projects. |
| OCR fails | Read the persisted extraction error; check engine/English data, page/image limits and readability. Failed reprocessing preserves earlier evidence. |
| Source PDF returns 404 | Confirm registered file exists inside configured uploads and the configured uploads root and source references still match; restore missing files from the matching backup. |
| Slow upload or comparison | Extraction has a 90-second document deadline, but no global concurrency bound. Dense comparisons remain quadratic and load all facts. See measured workload limits below. |
| Stale evidence after failure/restart | Reload document status and inspect original PDF; retained facts can be from the earlier successful run. No extraction history or durable task queue exists. |

Upload accepts at most 10 MiB using bounded handler reads and temporary-file publication. Multipart parsing/spooling still occurs before the handler; no whole-request resource cap is implemented. Extraction allows 40 pages, 300-DPI rendering, 12 million pixels/page, and 20 seconds per OCR call. These are not a total-memory quota or throughput guarantee. Native/OCR evidence and comparisons require manual source review.

## Verified schema-3 recovery procedure

1. Stop the API and allow workers to exit. For legacy schema 0/1/2, first back up and migrate at its original root using compatible code; do not move before migration.
2. Archive the entire schema-3 data directory, including uploads. Keep the original/archive until recovery checks pass. Extract a trusted archive into a new empty destination; never merge it over another collection.
3. Start a fresh backend process with FACTFLOW_DATA_DIR set to the restored directory containing factlayer.db and uploads. API source paths should now point inside that directory.
4. Check SQLite `PRAGMA integrity_check` (ok) and `PRAGMA foreign_key_check` (no rows) with the API stopped. Compare document/fact counts, IDs, provenance, and source-file hashes against the backup. Reopen facts, original PDFs, and comparisons in the browser. Retained-extraction warnings must survive.
5. On a disposable verification copy, confirm reprocessing replaces fact IDs, deletion removes only restored sources, and new uploads land in the new root. Do not treat reprocessing as a non-mutating verification step.

A database-only or incomplete archive cannot recover missing source bytes: source access returns 404 and failed reprocessing retains facts. There is no fallback to the old location. A legacy archive moved before migration is rejected without changing its database; restore it at the original root first. These checks do not establish crash consistency, live-backup safety, or off-machine archival durability.

## Verification and remaining scope

Part 8 is complete. Current checks: **87 backend tests, 12 mocked desktop/mobile browser checks, two real browser/API workflows, and production build pass**. Backend recovery tests use separate seed/restore processes with real native/OCR fixtures and archive restoration. Same-path, relocated, missing-source, and moved-legacy cases pass. Browser startup uses the restored collection with the original path unavailable; source bytes, provenance, retained warnings, comparisons, reprocessing, and deletion are checked. The existing upload lifecycle runs afterward.

Reproduce with the README backend, browser mock, integration, and build commands. Run only the recovery cases from backend with `.venv/bin/python -m pytest -q tests/test_storage_recovery.py`. Tesseract with English data and locked Python dependencies are required for the real OCR fixtures. Ports remain 5189 for mocks and 5190/8029 for integration. All fixture storage is temporary; normal local data is never imported by the recovery probes.

SHA-256 checks before/after untracking confirmed all six local files were preserved and ignored. No live-data migration, deployment, dependency change, or commit was performed. Local single-user scope remains. Part 9 Phase 1 now adds bounded upload copying and handled-failure cleanup; see the [ingestion plan and limits](ingestion-reliability.md). See [storage acceptance gates](storage-portability-plan.md), [OCR measurements](ocr-plan.md), [collection benchmarks](collection-performance.md), and [comparison evaluation](comparison-quality.md) for limits.

## Part 9 Phase 1 checkpoint

98 backend tests and both real integration workflows pass. Copy/storage failure removes temporary files; database registration failure removes the unpublished-to-metadata source, provided unlink succeeds. A successful registration followed by extraction failure still retains the source. File/DB publication is not crash-atomic; interrupted processes can leave orphan files. Inspect Documents before retrying a request with a lost response. Extraction admission and mutation coordination remain Phase 2; frontend/build results above are historical Part 8 checks.
