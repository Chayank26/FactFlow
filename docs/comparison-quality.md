# Comparison quality evaluation — Part 7 Phase 2

## Dataset and rubric

The [48 labeled pairs](../backend/evaluation/comparison_cases.json) are agent-authored synthetic English examples, with source IDs, page references, full claim text, categories, and label rationales. Each of the development and holdout splits contains four agreements, twelve useful review pairs, and eight unrelated pairs. These are synthetic source records, not extracted PDFs.

- `agreement`: matching wording after case/whitespace normalization and trailing `. ! ?` removal. This does not establish truth or entailment.
- `difference`: useful to review together, including paraphrases and changes in quantity, negation, units, roles, time, scope, or signs. This does not mean contradiction.
- `none`: unrelated under the authored rubric, even if generic wording overlaps.

The evaluation exercises already-extracted claim pairs through the production candidate generator. It does not measure OCR, extraction, ranking, or collection-level usefulness. Source/page preservation is separately checked at the API boundary.

## Method and results

Development thresholds were declared as 0.5, 0.6, and 0.7. Select the highest development macro-F1, preferring the threshold closest to baseline on ties. Development-only evaluation selected 0.6 (macro-F1 0.7661 versus baseline 0.7613). Holdout was evaluated after selection; it was not used to tune the threshold. The checked-in [raw report](comparison-evaluation.json) includes confusion matrices, per-label precision/recall/F1, category counts, predictions, and error IDs linked to corpus rationales.

| Holdout metric (24 pairs) | Production 0.5 | Candidate 0.6 |
| --- | ---: | ---: |
| Correct classifications | 15/24 | 16/24 |
| Macro-F1 | 0.6931 | 0.7306 |
| Review-pair precision | 73.33% | 78.57% |
| Review-pair recall | 68.75% | 68.75% |
| Unrelated pairs surfaced | 4 | 3 |
| Related pairs missed | 5 | 5 |

Review-pair precision/recall combine agreement and difference as positive. Macro-F1 averages all three label F1 scores. Baseline agreement precision/recall are 100% on just four examples; difference precision/recall are 63.64%/58.33%; none precision/recall are 44.44%/50%.

Baseline errors include one negation, three paraphrases, and one contextual pair missed, plus one different-subject and three generic-wording pairs surfaced. The candidate removes one generic-wording false positive. Read the error records and source text together; the labels express review usefulness, not independently verified facts.

## Decision and limits

**Retain production threshold 0.5.** The candidate passes the declared screening gate (higher holdout macro-F1 and review precision, at most 0.05 recall loss), but its one-case gain does not justify production promotion. The optional threshold argument is used by offline evaluation; API defaults and relationship semantics remain unchanged.

These labels have one author and no independent adjudication. Both splits were authored together with similar patterns; the holdout is neither blind nor representative of actual documents. Balanced labels do not reflect production prevalence. The numbers are descriptive counts, not an accuracy guarantee, significance claim, or confidence estimate. The holdout is now consumed: further tuning needs fresh evaluation examples.

A future quality phase should collect representative, consented document pairs, independently annotate and adjudicate review usefulness, and evaluate fresh splits before changing the heuristic or comparing semantic models. Embeddings/model calls could address paraphrases but introduce dependencies, costs, privacy choices, and different errors; this corpus cannot establish that trade-off. No model or dependency was added.

Part 7 Phase 3 remains operational reconciliation and the local-versus-deployment scope decision.

## Reproduce

From the repository root (no server, model, OCR engine, or runtime database needed):

```sh
backend/.venv/bin/python backend/scripts/evaluate_comparisons.py --development-only --output /tmp/factflow-comparison-development.json
backend/.venv/bin/python backend/scripts/evaluate_comparisons.py --output /tmp/factflow-comparison-evaluation.json
cmp docs/comparison-evaluation.json /tmp/factflow-comparison-evaluation.json
```

The runner imports pure comparison helpers, never the API/storage module. Backend tests check corpus structure and split separation, hand-calculated metrics, selection independence from holdout labels, exact report reproduction, and API parity/provenance for all 48 pairs. Existing exhaustive-reference tests guard unchanged production behavior.
