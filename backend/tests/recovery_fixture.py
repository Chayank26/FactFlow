"""Fresh-process recovery probe, always configured with disposable storage."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def run(mode, manifest):
    # Caller must set FACTFLOW_DATA_DIR before this module imports the API.
    import os
    assert os.environ.get('FACTFLOW_DATA_DIR'), 'Explicit disposable storage required'
    from app import main
    from fastapi.testclient import TestClient
    from tests.pdf_fixtures import make_pdf
    from tests.ocr_fixtures import scan
    client = TestClient(main.app)
    if mode == 'seed':
        sources = []
        for name, content in [('native.pdf', make_pdf('Revenue increased 20 percent.')), ('scan.pdf', scan())]:
            response = client.post('/documents', files={'file': (name, content, 'application/pdf')})
            assert response.status_code == 200
            doc = response.json()
            assert doc['status'] == 'processed'
            sources.append({'id': doc['id'], 'filename': name, 'sha256': hashlib.sha256(content).hexdigest()})
        # Preserve a real failed-run warning with a restored original source.
        path = Path(client.get('/documents').json()['items'][0]['stored_path'])
        original = path.read_bytes()
        path.write_bytes(b'broken PDF')
        assert client.post(f"/documents/{sources[-1]['id']}/process").status_code == 422
        path.write_bytes(original)
        manifest.write_text(json.dumps({'sources': sources, 'documents': client.get('/documents').json(), 'facts': client.get('/facts').json()}))
    else:
        expected = json.loads(manifest.read_text())
        assert client.get('/facts').json() == expected['facts']
        actual = client.get('/documents').json()
        for old, new in zip(expected['documents']['items'], actual['items']):
            assert {k:v for k,v in old.items() if k != 'stored_path'} == {k:v for k,v in new.items() if k != 'stored_path'}
            assert Path(new['stored_path']).parent == main.UPLOADS_DIR
        with sqlite3.connect(main.DB_PATH) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert db.execute('PRAGMA foreign_key_check').fetchall() == []
            assert db.execute('PRAGMA user_version').fetchone()[0] == 3
        for source in expected['sources']:
            response = client.get(f"/documents/{source['id']}/source")
            if mode == 'missing':
                assert response.status_code == 404
            else:
                assert response.status_code == 200
                assert hashlib.sha256(response.content).hexdigest() == source['sha256']
        if mode == 'mutate':
            for source in expected['sources']:
                assert client.post(f"/documents/{source['id']}/process").status_code == 200
                old_ids = {f['id'] for f in expected['facts']['items']}
                assert not old_ids.intersection(f['id'] for f in client.get('/facts', params={'document_id': source['id']}).json()['items'])
                assert client.delete(f"/documents/{source['id']}").status_code == 204
            response = client.post('/documents', files={'file': ('new.pdf', make_pdf('Costs decreased five percent.'), 'application/pdf')})
            assert response.json()['status'] == 'processed'
            assert Path(response.json()['stored_path']).parent == main.UPLOADS_DIR
        if mode == 'missing':
            for source in expected['sources']:
                assert client.post(f"/documents/{source['id']}/process").status_code == 422
            assert {f['id'] for f in client.get('/facts').json()['items']} == {f['id'] for f in expected['facts']['items']}
    print('Recovery probe passed:', mode)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['seed', 'verify', 'mutate', 'missing'])
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    run(args.mode, args.manifest)
