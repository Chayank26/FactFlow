"""Comparison/retrieval benchmark; creates only temporary application storage."""
import argparse
import json
import os
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def exhaustive(rows, tokenize, normalize):
    for i, left in enumerate(rows):
        a = tokenize(left['claim'])
        if not a:
            continue
        for j in range(i + 1, len(rows)):
            right = rows[j]
            if left['document_id'] == right['document_id']:
                continue
            b = tokenize(right['claim'])
            if not b:
                continue
            shared = a & b
            if normalize(left['claim']) == normalize(right['claim']):
                yield i, j, 'agreement'
            elif len(shared) >= 2 and len(shared) / max(len(a), len(b)) >= 0.5:
                yield i, j, 'difference'


def timed(call):
    start = perf_counter()
    result = call()
    return result, round(perf_counter() - start, 6)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'machine': platform.platform(), 'python': platform.python_version(), 'cases': []}
    with TemporaryDirectory(prefix='factflow-collections-') as storage:
        os.environ['FACTFLOW_DATA_DIR'] = storage
        from app.main import app, get_connection, claim_tokens, normalized_claim
        from app.comparison_candidates import candidate_pairs
        from fastapi.testclient import TestClient
        client = TestClient(app)
        for count, dense in [(200, False), (1000, False), (2000, False), (1000, True)]:
            rows = [{'document_id': f'd{i % 100:03}', 'claim': ('Revenue increased 20 percent.' if dense else f'topic{i // 10} metric{i // 10} value{i % 10}')} for i in range(count)]
            baseline, baseline_seconds = timed(lambda: list(exhaustive(rows, claim_tokens, normalized_claim)))
            indexed, indexed_seconds = timed(lambda: list(candidate_pairs(rows, claim_tokens, normalized_claim)))
            assert baseline == indexed
            with get_connection() as connection:
                connection.execute('DELETE FROM facts')
                connection.execute('DELETE FROM documents')
                for i in range(100):
                    connection.execute('INSERT INTO documents (id, filename, size_bytes, stored_path, created_at, status) VALUES (?, ?, 0, ?, ?, ?)', (f'd{i:03}', f'source-{i}.pdf', 'unused.pdf', 'now', 'processed'))
                connection.executemany('INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at) VALUES (?, ?, ?, 1, ?, ?)', [(f'f{i:05}', r['document_id'], r['claim'], r['claim'], 'now') for i, r in enumerate(rows)])
            endpoints = {}
            for path in ['/documents', '/facts', '/comparisons']:
                response, seconds = timed(lambda: client.get(path, params={'limit': 20}))
                assert response.status_code == 200
                page = response.json()
                assert len(page['items']) <= 20
                endpoints[path] = {'seconds': seconds, 'items': len(page['items']), 'total': page['total'], 'bytes': len(response.content)}
            record = {'facts': count, 'documents': 100, 'shape': 'dense-identical' if dense else 'sparse-ten-claim-topics', 'all_unordered_pairs': count*(count-1)//2, 'matching_pairs': len(indexed), 'exhaustive_seconds': baseline_seconds, 'indexed_seconds': indexed_seconds, 'endpoints': endpoints}
            report['cases'].append(record)
            print(json.dumps(record), flush=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
