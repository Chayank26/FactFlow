# Part 8 — Storage portability and recovery

Phase 1 specification, 2026-10-03. **Planned behavior, not implemented:** current storage remains schema 2 with absolute paths and verified same-path recovery only.

## Three phases

1. Specification: audit consumers and define migration, compatibility, fixtures, and failure outcomes. Checkpoint: specification coverage and passing baseline checks.
2. Implementation: portable references, shared path resolver, transactional migration and regression tests. Checkpoint: migration, containment, idempotence, and preserved evidence verified.
3. Recovery verification and repository hygiene: relocated restore through API/browser workflows; reconcile tracked artifacts while preserving local files. Checkpoint: relocation/recovery passes and documentation reflects actual behavior. No history rewrite or deletion of the user's collection.

Local single-user scope remains unchanged; no hosting, accounts, queue, or model is introduced.

## Current audit

`backend/app/main.py` resolves FACTFLOW_DATA_DIR at import, initializes schema 2, and stores absolute `documents.stored_path` values. Upload, document serialization, reprocessing, source serving, and deletion consume this path. Only source serving currently checks upload-directory containment.

Backend tests and `frontend/integration/documents.spec.js` inspect returned absolute paths. The browser links to the source endpoint. Preserve that response contract. Legacy migration tests contain `/old.pdf`; scale/evaluation seeds contain `/unused`. Update fixtures to realistic paths or explicit rejection cases during implementation rather than weaken validation.

Git still tracks a legacy database and five uploads despite the ignore rule. This phase does not import the API against that collection, migrate it, or untrack it.

## Planned reference contract

At schema 3, retain the database column name `stored_path` but store only the existing generated filename relative to UPLOADS_DIR: one nonempty component, not `uploads/name`. Preserve document/fact IDs, original filenames, timestamps, status/errors, extraction method, and source bytes. Do not rename or rewrite PDFs.

Use one resolver for source retrieval, reprocessing, deletion, and response serialization. Reject absolute schema-3 references, `.`, `..`, separators including backslashes, NUL, source-file symlinks, and resolution outside the configured uploads root. Distinguish valid-but-missing sources from invalid references. This local containment check is not a defense against a hostile local process racing filesystem operations.

For valid references, the API continues returning an absolute `stored_path`, computed for the current root. For invalid/tampered references, metadata returns an empty stored_path and source actions reject access. Source links remain `/documents/{id}/source`.

Source retrieval returns 404 for missing/invalid files. Invalid references cause process/delete to return 409 before changing rows or touching files. Missing valid sources follow current failed-reprocess semantics: failure status with retained facts; deletion can remove their metadata. For present valid sources, attempt unlink before committing row removal; unlink failure preserves metadata/facts for retry. Filesystem and SQLite changes are not atomic together: a later database failure can leave retained metadata with a missing file. Do not claim crash-atomic deletion.

## Migration and rollback

Require a stopped-app whole-directory backup before upgrading an existing collection. All implementation checks use temporary roots; do not start new code against the user's default collection as a test.

- New databases initialize schema 3. Versions 0/1/2 upgrade in one explicit transaction encompassing schema, indexes, path edits, and version. Reject newer versions before changes.
- Preflight every legacy path: absolute, a direct child of the current uploads root, no traversal components or symlink. Reject duplicate references. Missing files inside the valid root preserve metadata and do not block migration.
- Store the accepted filename only. Unexpected relative values, nested or out-of-root paths abort the whole migration with document IDs and recovery guidance. Never infer ownership from basename alone, search other directories, follow external links, or silently discard rows.
- Set version 3 only on successful commit. Injected failure must roll back schema/data/version. Repeated initialization must be idempotent.
- Restore/migrate schema-2 archives at their original root before moving them as schema 3. Already-relocated legacy archives are not automatically remapped; explicit old-root mapping tooling is deferred.
- Downgrade is unsupported. Rollback means restoring the whole pre-upgrade backup at its original path with compatible application code.

Helper names may change during implementation; changes to preservation/failure guarantees require updating this specification and tests together.

## Required fixtures and gates

Fixtures below are **specified, not generated or passed in Phase 1**. Use temporary roots A/B, generated PDFs, snapshots/hashes, and an outside sentinel that must remain untouched.

| Fixture | Acceptance gate | Phase |
| --- | --- | --- |
| New collection | Relative DB reference, absolute API path; upload/source/process/delete work | 2 |
| Schema 0/1/2, native and retained failed evidence | Version 3; IDs/text/pages/status/errors/bytes preserved; legacy method defaults native; repeated startup unchanged | 2 |
| Mixed valid/invalid legacy rows | Whole migration rolls back, including schema/version; error identifies invalid row | 2 |
| Injected mid-migration failure; future version | No partial migration; future schema unchanged | 2 |
| Missing in-root source | Migration retains facts; source 404; processing fails preserving facts; deletion works | 2 |
| Outside, traversal, nested, duplicate, symlink, relative legacy references | Refuse migration; sentinel never read/written/deleted | 2 |
| Tampered schema-3 paths | Source 404; process/delete 409; rows/sentinel unchanged; metadata hides invalid path | 2 |
| Unlink failure injection | Metadata/facts retained; retry succeeds after fault removed | 2 |
| Whole schema-3 archive A restored to B, A unavailable | Fresh process at B; identical source bytes and pre-reprocess facts/IDs/status; upload/process/delete affect only B | 3 |
| Native/OCR and retained failed evidence | Relocation preserves provenance/warnings/pages; successful reprocessing replaces facts normally | 3 |
| Database-only/incomplete archive | Missing source explicit; no fallback to A or silent loss of retained evidence | 3 |
| Legacy archive moved before migration | No automatic remapping; restore-at-original-root guidance | 3 |
| Same-path restore | SQLite integrity/foreign-key checks and source hashes/metadata match before mutations | 3 |
| Tracked runtime cleanup | Preserve local bytes/usability, review tracked removals, ignore future runtime changes; no history rewrite | 3 |

Phase 2 runs backend tests and real browser/API integration for response-path compatibility. Phase 3 runs backend tests, browser mocks, real integration, frontend build, and an isolated relocation drill. Copy archives only with API/workers stopped and connections closed. No live-backup or power-loss guarantee follows.

## Tools and trade-offs

No new dependency is planned: pathlib/sqlite3 for implementation; tempfile/tarfile/hashlib, pytest and Playwright for checks. A separate storage-key column clarifies naming but duplicates migration/compatibility state; versioning the retained column is smaller. Absolute paths require rewrites after each move. Remote storage or an ORM/migration framework adds requirements absent from this local app.

## Phase 1 checkpoint

Specification reviewed against schema initialization, upload, serialization, source/process/delete and existing tests; baseline backend suite passes. No schema-3, relocation, new containment, or tracked-file cleanup claim is made. See [operations](operations.md) for currently supported behavior.
