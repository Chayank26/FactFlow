import copy
import json
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app, get_connection
from app.comparison_candidates import normalized_claim
from scripts.evaluate_comparisons import DEFAULT_CASES, predict, report, summarize

CORPUS = json.loads(DEFAULT_CASES.read_text())


def test_corpus_has_disjoint_balanced_splits_and_traceable_sources():
    cases = CORPUS['cases']
    assert len({case['id'] for case in cases}) == len(cases) == 48
    pairs = {}
    for split in ('development', 'holdout'):
        selected = [case for case in cases if case['split'] == split]
        assert Counter(case['expected'] for case in selected) == {'agreement': 4, 'difference': 12, 'none': 8}
        pairs[split] = {tuple(sorted(normalized_claim(case[side]['text']) for side in ('left', 'right'))) for case in selected}
        for case in selected:
            assert case['rationale'] and case['category']
            assert case['left']['document_id'] != case['right']['document_id']
            assert all(case[side]['page'] > 0 and case[side]['text'] for side in ('left', 'right'))
    assert pairs['development'].isdisjoint(pairs['holdout'])


def test_metrics_match_hand_calculation():
    metrics = summarize([{'expected': a, 'predicted': p, 'category': 'example'} for a, p in [
        ('agreement', 'agreement'), ('difference', 'none'), ('none', 'difference'), ('none', 'none'),
    ]])
    assert metrics['accuracy'] == metrics['macro_f1'] == 0.5
    assert metrics['review_pair_precision'] == metrics['review_pair_recall'] == 0.5
    assert metrics['per_label']['none'] == {'precision': 0.5, 'recall': 0.5, 'f1': 0.5, 'support': 2}


def test_threshold_selection_does_not_use_holdout_labels():
    changed = copy.deepcopy(CORPUS)
    for case in changed['cases']:
        if case['split'] == 'holdout':
            case['expected'] = 'agreement'
    assert report(changed)['selected_threshold'] == report(CORPUS, development_only=True)['selected_threshold'] == 0.6


def test_checked_in_evaluation_is_reproducible():
    saved = Path(__file__).resolve().parents[2] / 'docs/comparison-evaluation.json'
    assert report(CORPUS) == json.loads(saved.read_text())


def test_api_matches_offline_baseline_and_preserves_source_evidence():
    client = TestClient(app)
    for case in CORPUS['cases']:
        with get_connection() as connection:
            connection.execute('DELETE FROM facts')
            connection.execute('DELETE FROM documents')
            for side in ('left', 'right'):
                source = case[side]
                connection.execute('INSERT INTO documents (id, filename, size_bytes, stored_path, created_at, status) VALUES (?, ?, 0, ?, ?, ?)', (source['document_id'], side + '.pdf', '/unused', side, 'processed'))
                connection.execute('INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at) VALUES (?, ?, ?, ?, ?, ?)', (side, source['document_id'], source['text'], source['page'], source['text'], side))
        response = client.get('/comparisons')
        assert response.status_code == 200
        items = response.json()['items']
        assert (items[0]['relationship'] if items else 'none') == predict(case, 0.5), case['id']
        if items:
            for side in ('left', 'right'):
                source = next(case[s] for s in ('left', 'right') if case[s]['document_id'] == items[0][side + '_document_id'])
                assert items[0][side + '_source_text'] == source['text']
                assert items[0][side + '_page'] == source['page']
