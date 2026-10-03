# Local operations and deployment decision

Part 7 Phase 3, verified 2026-10-03.

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
| Schema | SQLite version 2, initialized/upgraded on startup; no downgrade tooling. |

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

Restore a trusted archive with the API stopped. Move the existing data directory to a dated recovery location first, then extract the backup into the original parent directory (`tar -xzf <archive> -C backend` for the default example). Preserve the exact original absolute data path: database records store absolute PDF paths. Relocation requires a separate path migration, which is not implemented. Starting with an empty directory is not a migration.

Before resuming work, check SQLite integrity and schema, then confirm Documents/Facts and an original PDF. On a disposable copy restored at its original path, also verify reprocessing and deletion; those mutate records. Successful reprocessing replaces fact IDs. Do not assume copying only the database recovers PDFs. Do not reset a collection without a verified backup.

**Verified recovery checkpoint:** an isolated temporary collection was uploaded, archived while idle, moved aside, and restored to its original absolute path. SQLite integrity returned `ok`, schema remained 2, facts and original PDF bytes matched, and subsequent `/documents/{id}/process` and deletion succeeded. This tests local same-path recovery, not relocation, crash consistency, live backups, or external archival durability. The live local collection was untouched.

## Repository data caveat

`.gitignore` excludes new `backend/data/` files, but Git still tracks a legacy database and five sample text uploads. Ignore rules do not untrack existing files. Check with `git ls-files backend/data` and inspect `git status --short` before commits. This phase preserves those files and Git history. A separate repository-hygiene change can remove tracked runtime artifacts after reviewing their preservation needs. Using a fresh external `FACTFLOW_DATA_DIR` avoids modifying those tracked files during new local work.

## Troubleshooting and limits

| Symptom | Check/action |
| --- | --- |
| Browser offline or fetch failure | Confirm API 8019, browser API URL, and exact allowed frontend origin; restart configuration changes. Preview port 4173 is not in default CORS origins. |
| Port already in use | Stop your own prior server or consistently change client/API/CORS ports; do not stop unrelated projects. |
| OCR fails | Read the persisted extraction error; check engine/English data, page/image limits and readability. Failed reprocessing preserves earlier evidence. |
| Source PDF returns 404 | Confirm registered file exists inside configured uploads and absolute paths still match; restore missing files from the matching backup. |
| Slow upload or comparison | Extraction has a 90-second document deadline, but no global concurrency bound. Dense comparisons remain quadratic and load all facts. See measured workload limits below. |
| Stale evidence after failure/restart | Reload document status and inspect original PDF; retained facts can be from the earlier successful run. No extraction history or durable task queue exists. |

Upload accepts at most 10 MB after reading the body into memory. Extraction allows 40 pages, 300-DPI rendering, 12 million pixels/page, and 20 seconds per OCR call. These are not a total-memory quota or throughput guarantee. Native/OCR evidence and comparisons require manual source review.

## Verification and next work

Current checkpoint: 61 backend tests pass; isolated same-path recovery passes. Documentation changes introduce no runtime code or dependencies; frontend build/browser checks were not rerun. Existing Part 7 Phase 1 evidence remains 12 mocked browser checks, one real PDF/OCR integration workflow, and a frontend build—not a new run for this phase.

Reproduce backend checks using the README command. Dedicated test ports are 5189 for browser mocks, and 5190/8029 for real browser/API integration; test storage is temporary. See [OCR measurements](ocr-plan.md), [collection performance](collection-performance.md), and [comparison evaluation](comparison-quality.md) for synthetic workload assumptions and reproduction commands.

Part 8 has started: [Phase 1 specification](storage-portability-plan.md) is complete. Its three phases are specification, portable references/migration, and relocation/recovery verification with repository hygiene. The latter two remain planned; current schema-2 storage and same-path recovery limitations still apply. No deployment is authorized or implemented by this work.
