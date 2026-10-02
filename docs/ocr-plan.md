# Part 6 — OCR readiness and acceptance plan

Phase 1 defines the corpus, acceptance gates, and implementation direction. OCR is not installed or implemented, and no recognition benchmark has been run. Phases 2–3 remain planned.

## Three phases

1. **Readiness (complete):** define representative fixtures, document acceptance criteria, inspect local capabilities, and compare implementations.
2. **OCR extraction:** materialize the corpus, install and verify dependencies, implement page-aware fallback with explicit failures and provenance, and run the acceptance checks below.
3. **Processing experience:** measure latency/resource use, decide whether background execution is needed, and verify progress, retries, cancellation/failure handling, and reprocessing. A queue is not predetermined.

## Fixture specification

Generate synthetic fixtures into temporary test storage; commit generators and expected text, not personal documents. These are specifications, not an already generated or benchmarked corpus. Each scanned fixture must contain a raster image with no selectable text; assert that pypdf returns no text on that page before using it to test OCR. Use a fixed bundled or explicitly located font and record raster resolution. Start with English printed text at 300 DPI; real-world scan accuracy will require a broader later corpus.

| Case | Construction | Ground truth / required outcome |
|---|---|---|
| Text-only control | Two selectable-text pages | Page 1: `Revenue increased 20 percent.` Page 2: `Costs decreased 5 percent.` Existing parser results unchanged; no OCR required. |
| Clean scanned | Raster-only page | `Revenue increased 20 percent.` Exact claim, number, unit, and page 1 recovered. |
| Mixed pages | Text page followed by raster-only page | Same two claims as control, on pages 1 and 2 respectively; neither omitted. |
| Same-page mixed content | Selectable heading `Quarterly report` plus raster claim | `Costs decreased 5 percent.` recovered once on page 1; a text heading must not automatically suppress OCR. |
| Numeric/negation | Raster-only page | `Revenue did not increase 20 percent.` and `The dose was 5 mg.` Negation, 20, 5, and mg preserved exactly. |
| Rotated/degraded | Clean scanned case rotated 90 degrees; separate lower-resolution/skewed variant | Record actual result; either recover expected text or report unsupported/failed handling explicitly. Do not claim universal rotation/noise support. |
| Blank/malformed | Truly blank valid PDF and invalid bytes | No invented facts; explicit extraction failure with source retained. |
| Duplicate evidence | Same claim in native text and raster content | Preserve deterministic document-level deduplication and a real source page; no duplicate fact introduced by merging extraction methods. |

Missing engine/language data, renderer failure, timeout, excessive page/render budget, and encrypted input are separate operational fixtures. Tests must distinguish successful extraction from incomplete/failed processing. Decide how incomplete pages are represented before enabling OCR; an unreadable page must not silently disappear behind a document-wide processed status.

## Phase 2 acceptance gates

- Verify actual raster-only fixture properties, then test through the real upload and reprocess endpoints in isolated storage.
- Clean scan, mixed-page, same-page mixed, numeric/negation, and text-control cases must meet their exact expected claims/pages after whitespace normalization. This is a regression gate for synthetic fixtures, not an accuracy percentage for arbitrary documents.
- Preserve original PDF bytes and page numbering. Source links still serve the original, not a substituted OCR-generated PDF.
- Record extraction method (native text/OCR) and report meaningful failures. Do not interpret engine confidence as proof of truth.
- Keep prior successful evidence on failed reprocessing, retain the earlier-run warning, and replace facts only after the new extraction is accepted.
- Bound page count, raster dimensions, per-page OCR time, and total processing time before enabling the fallback. Select concrete limits after measurements; never silently skip exceeded limits.
- Retain existing text-PDF, provenance, deletion, comparison, API, and browser regression checks. Add a real scanned-PDF browser workflow once dependencies work.
- Engine/language availability must be checked and failure explained; the native-text path should remain usable without OCR.

## Local capability inspection

At Phase 1 inspection, `tesseract`, `pdftoppm`, and `ocrmypdf` were not on PATH. The backend virtual environment had no Pillow, pypdfium2, or pytesseract. Existing pypdf can read text but does not supply the proposed raster/OCR stack. No OCR dependencies were installed in this phase.

## Evaluated approaches and provisional decision

| Approach | Fit | Trade-off |
|---|---|---|
| Tesseract CLI + pypdfium2 rendering | Preferred starting point: explicit page processing, local execution, and existing fact pipeline reuse | Requires a native engine/language data and PDF renderer; FactFlow must implement limits, mixed-content selection, merging, and failure handling. |
| OCRmyPDF | Useful if generating searchable derivative PDFs becomes a product requirement | Broader PDF-processing/dependency surface; original-versus-derived source handling adds complexity for this app. Evaluate mixed-content behavior rather than assuming skip-text modes solve it. |
| Hosted OCR | Possible future option | Sends source data externally and adds credentials, cost, and network availability concerns; inconsistent with the current local-only scope. No provider selected. |

**Decision:** provisionally use pypdfium2 to render selected pages and Tesseract CLI for OCR, retaining pypdf for native text and the existing fact pipeline. Confirm compatibility, English language data, and fixture results in Phase 2 before locking versions. Pillow may be used for fixture generation/image conversion if required. This is an architectural choice, not a measured quality/performance result.

Tesseract takes images rather than PDF input, so rendering is necessary. pypdfium2 supplies PDF rendering and prebuilt wheels for supported platforms. OCRmyPDF provides a larger ready-made PDF workflow. Primary references reviewed for this decision:

- [Tesseract input formats](https://tesseract-ocr.github.io/tessdoc/InputFormats.html)
- [Tesseract command-line usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)
- [pypdfium2 introduction and installation](https://pypdfium2-team.github.io/pypdfium2/readme.html)
- [OCRmyPDF installation](https://ocrmypdf.readthedocs.io/en/stable/installation.html)

## Phase 3 measurement gate

Record engine/renderer versions, machine, language data, pages/DPI, per-page and total wall time, and memory observations for single-page and multi-page fixtures. Set an interactive latency budget before judging results. If synchronous processing exceeds it, design bounded background execution with explicit job state and retry behavior; otherwise retain synchronous processing and document the measured limit. No performance numbers or background-worker decision exist yet.
