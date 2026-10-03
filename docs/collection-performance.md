# Part 7 Phase 1 — Collection retrieval and comparison performance

## API contract

GET /documents and GET /comparisons now return `{items, total, limit, offset}`, matching GET /facts. This replaces the earlier array responses: clients must read `items` and use `total` for counts. Default limit is 50, accepted limits are 1–100, and offsets must be nonnegative. Document filename search is `search` with SQLite LIKE semantics. Comparison document/relationship filters retain their meaning and run before counting/paging results.

Browser lists and source selectors request 20 items. Documents/Comparisons have Previous/Next controls; source selectors search filenames and page independently, preserving selected IDs outside the visible option page. Filter changes reset comparison offsets. Deletion/result shrink moves an invalid offset back to a valid page. Counts come from API totals rather than page lengths. Source processing status now accompanies fact/comparison evidence, so a source absent from the current document page still has its retained-evidence warning.

## Candidate index

Previously the comparison loop visited every cross-document pair and tokenized the right claim repeatedly. The implementation now computes token sets and normalized wording once, builds token and exact-wording postings, and evaluates pairs sharing at least two meaningful tokens plus exact matches. The exact-match path preserves agreements with only one meaningful token. Same-document pairs remain excluded; source and relationship filters are unchanged. Results retain the previous fact ordering and pair orientation.

A seeded regression compares ordered indexed output to an exhaustive reference, including empty-token claims, one-term agreements, reordered words, and source filters. Paginated regression tests traverse all 300 pairs from 25 equal claims without duplicates. This is an optimization of the existing rule, not a claim that the rule understands truth or semantic agreement.

Only requested comparison cards are constructed, although all matching pairs are counted for an exact total. All fact rows/token indexes remain in memory per request. Dense shared vocabulary can still cause quadratic work; pagination bounds responses, not total CPU or database size. There is no persisted comparison cache, full-text index, cursor snapshot, or arbitrary-scale guarantee. Offset pages may shift after mutations.

## Measurements

Single local run on macOS 26.5.2 arm64, Python 3.13.9, temporary SQLite storage, 100 synthetic documents. Sparse datasets group ten claims by topic; the dense dataset repeats identical claims. The reference reproduces the previous matching loop. Timings below compare complete match generation (including list materialization) and assert identical ordered results, not a before/after deployed HTTP service benchmark.

| Facts / shape | Exhaustive matching | Indexed matching | Matching pairs | Current /comparisons request, 20 items |
|---|---:|---:|---:|---:|
| 200 sparse | 17.1 ms | 0.8 ms | 900 | 3.3 ms |
| 1,000 sparse | 427.7 ms | 8.5 ms | 4,500 | 14.0 ms |
| 2,000 sparse | 1,706.8 ms | 27.6 ms | 9,000 | 34.0 ms |
| 1,000 dense | 475.6 ms | 182.8 ms | 495,000 | 215.9 ms |

Each request returned at most 20 items. Document/fact/comparison response sizes and total counts are recorded in [collection-benchmark.json](collection-benchmark.json). API times use FastAPI TestClient, excluding actual network transport; initial startup/connection overhead can affect the first sample. No concurrency or peak-memory benchmark was run. These synthetic results do not predict every real collection.

Reproduce from backend/:

```sh
.venv/bin/python scripts/benchmark_collections.py --output ../docs/collection-benchmark.json
```

The script overrides FACTFLOW_DATA_DIR before importing the application and removes its temporary storage afterward. It never uses local uploaded PDFs.

## Checkpoint

56 backend tests, 12 mocked desktop/mobile browser checks, the real PDF/OCR integration workflow, production frontend build, and whitespace checks pass. New browser coverage reaches documents beyond page one, pages/searches source options, traverses comparison pages, and resets offsets on filtering. Part 7 Phase 2 (labeled quality evaluation) and Phase 3 (operational reconciliation) remain planned.
