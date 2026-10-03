"""Offline evaluation of review-pair usefulness; never imports the API/storage."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.comparison_candidates import candidate_pairs, claim_tokens, normalized_claim

LABELS = ('agreement', 'difference', 'none')
THRESHOLDS = (0.5, 0.6, 0.7)
DEFAULT_CASES = Path(__file__).resolve().parents[1] / 'evaluation/comparison_cases.json'


def predict(case, threshold):
    rows = [{'document_id': case[side]['document_id'], 'claim': case[side]['text']} for side in ('left', 'right')]
    result = list(candidate_pairs(rows, claim_tokens, normalized_claim, min_similarity=threshold))
    return result[0][2] if result else 'none'


def summarize(predictions):
    matrix = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    categories = {}
    for row in predictions:
        matrix[row['expected']][row['predicted']] += 1
        bucket = categories.setdefault(row['category'], {'correct': 0, 'total': 0})
        bucket['total'] += 1
        bucket['correct'] += row['expected'] == row['predicted']
    per_label = {}
    for label in LABELS:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        predicted = sum(matrix[actual][label] for actual in LABELS)
        precision = tp / predicted if predicted else 0
        recall = tp / support if support else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        per_label[label] = {'precision': precision, 'recall': recall, 'f1': f1, 'support': support}
    tp = sum(matrix[a][p] for a in LABELS[:2] for p in LABELS[:2])
    fp = sum(matrix['none'][p] for p in LABELS[:2])
    fn = sum(matrix[a]['none'] for a in LABELS[:2])
    return {
        'count': len(predictions), 'confusion_matrix_actual_then_predicted': matrix,
        'accuracy': sum(matrix[label][label] for label in LABELS) / len(predictions) if predictions else 0,
        'macro_f1': sum(row['f1'] for row in per_label.values()) / len(LABELS),
        'per_label': per_label, 'by_category': categories,
        'review_pair_precision': tp / (tp + fp) if tp + fp else 0,
        'review_pair_recall': tp / (tp + fn) if tp + fn else 0,
    }


def evaluate(cases, threshold):
    rows = [{'id': case['id'], 'category': case['category'], 'expected': case['expected'], 'predicted': predict(case, threshold), 'rationale': case['rationale']} for case in cases]
    return {'threshold': threshold, 'metrics': summarize(rows), 'predictions': rows, 'errors': [row for row in rows if row['expected'] != row['predicted']]}


def report(corpus, development_only=False):
    development = [case for case in corpus['cases'] if case['split'] == 'development']
    trials = [evaluate(development, threshold) for threshold in THRESHOLDS]
    # Predeclared: highest development macro-F1, baseline preference on ties.
    selected = max(trials, key=lambda trial: (trial['metrics']['macro_f1'], -abs(trial['threshold'] - 0.5)))
    result = {'dataset_version': corpus['version'], 'provenance': corpus['provenance'], 'selection_rule': 'Highest development macro-F1; prefer baseline on ties. Never select threshold using holdout.', 'development': trials, 'selected_threshold': selected['threshold']}
    if not development_only:
        holdout = [case for case in corpus['cases'] if case['split'] == 'holdout']
        baseline = evaluate(holdout, 0.5)
        candidate = evaluate(holdout, selected['threshold'])
        old, new = baseline['metrics'], candidate['metrics']
        # A tiny authored corpus is only a screening gate, never deployment proof.
        passes = new['macro_f1'] > old['macro_f1'] and new['review_pair_precision'] > old['review_pair_precision'] and new['review_pair_recall'] >= old['review_pair_recall'] - 0.05
        result.update({'holdout_baseline': baseline, 'holdout_candidate': candidate, 'screening_gate': 'Higher holdout macro-F1 and review-pair precision, with at most 0.05 recall loss.', 'passes_screening_gate': passes, 'production_threshold': 0.5})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=Path, default=DEFAULT_CASES)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--development-only', action='store_true')
    args = parser.parse_args()
    result = report(json.loads(args.cases.read_text()), args.development_only)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'selected_threshold': result['selected_threshold'], 'development_macro_f1': {str(row['threshold']): row['metrics']['macro_f1'] for row in result['development']}, 'holdout': {key: result[key]['metrics'] for key in ['holdout_baseline', 'holdout_candidate'] if key in result}}, indent=2))
