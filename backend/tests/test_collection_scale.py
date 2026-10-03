import random

from fastapi.testclient import TestClient
from app.main import app, claim_tokens, normalized_claim, get_connection
from app.comparison_candidates import candidate_pairs

client = TestClient(app)


def reference_pairs(rows, document_id=None):
    for index, left in enumerate(rows):
        left_tokens = claim_tokens(left['claim'])
        if not left_tokens:
            continue
        for right_index in range(index + 1, len(rows)):
            right = rows[right_index]
            if left['document_id'] == right['document_id']:
                continue
            if document_id and document_id not in (left['document_id'], right['document_id']):
                continue
            right_tokens = claim_tokens(right['claim'])
            if not right_tokens:
                continue
            shared = left_tokens & right_tokens
            if normalized_claim(left['claim']) == normalized_claim(right['claim']):
                yield index, right_index, 'agreement'
            elif len(shared) >= 2 and len(shared) / max(len(left_tokens), len(right_tokens)) >= 0.5:
                yield index, right_index, 'difference'


def test_index_matches_exhaustive_reference_including_single_term_agreement():
    randomizer = random.Random(731)
    claims = ['The the revenue.', 'THE THE REVENUE!', 'the and of', 'A acquired B.', 'B acquired A.']
    rows = [{'document_id': str(i % 7), 'claim': randomizer.choice(claims) if i < 20 else ' '.join(randomizer.choices(['revenue', 'cost', '20', '30', 'not', 'increased', 'decreased'], k=5))} for i in range(100)]
    for document_id in [None, '', '2', 'missing']:
        assert list(candidate_pairs(rows, claim_tokens, normalized_claim, document_id)) == list(reference_pairs(rows, document_id))


def seed(count=25):
    with get_connection() as connection:
        for i in range(count):
            connection.execute('INSERT INTO documents (id, filename, size_bytes, stored_path, created_at, status) VALUES (?, ?, 0, ?, ?, ?)', (f'd{i:03}', f'source-{i:03}.pdf', '/unused', 'same-time', 'extraction_failed' if i == 24 else 'processed'))
            connection.execute('INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at) VALUES (?, ?, ?, 1, ?, ?)', (f'f{i:03}', f'd{i:03}', 'Revenue increased 20 percent.', 'Revenue increased 20 percent.', 'same-time'))


def test_bounded_documents_and_comparisons_with_complete_stable_traversal():
    seed()
    documents = client.get('/documents', params={'limit': 20}).json()
    assert documents['total'] == 25
    assert len(documents['items']) == 20
    assert client.get('/documents', params={'search': '024'}).json()['items'][0]['id'] == 'd024'
    second = client.get('/documents', params={'limit': 20, 'offset': 20}).json()
    assert [item['id'] for item in documents['items'] + second['items']] == [f'd{i:03}' for i in range(25)]
    ids = []
    for offset in range(0, 300, 100):
        page = client.get('/comparisons', params={'limit': 100, 'offset': offset}).json()
        assert page['total'] == 300
        assert len(page['items']) == 100
        assert client.get('/comparisons', params={'limit': 100, 'offset': offset}).json() == page
        ids.extend(item['id'] for item in page['items'])
    assert len(set(ids)) == 300
    filtered = client.get('/comparisons', params={'document_id': 'd024', 'relationship': 'agreement'}).json()
    assert filtered['total'] == 24
    assert all(item['right_document_status'] == 'extraction_failed' for item in filtered['items'])
    assert client.get('/comparisons', params={'relationship': 'difference'}).json()['total'] == 0
    assert client.get('/comparisons', params={'offset': 300}).json()['items'] == []
    assert client.get('/facts', params={'document_id': 'd024'}).json()['items'][0]['document_status'] == 'extraction_failed'


def test_new_list_pagination_validation():
    for endpoint in ['/documents', '/comparisons']:
        for parameters in [{'limit': 0}, {'limit': 101}, {'offset': -1}]:
            assert client.get(endpoint, params=parameters).status_code == 422
