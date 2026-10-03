from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app import main
from tests.test_document_management import upload_pdf

client = TestClient(main.app)


def snapshot():
    with main.get_connection() as db:
        return '\n'.join(db.iterdump())


def legacy(version=2):
    doc = upload_pdf()
    with main.get_connection() as db:
        db.execute('UPDATE documents SET stored_path = ?, status = ?, extraction_error = ?', (doc['stored_path'], 'extraction_failed', 'previous failure'))
        db.execute(f'PRAGMA user_version = {version}')
    return doc


@pytest.mark.parametrize('version', [0, 1, 2])
def test_upgrade_preserves_evidence(version):
    doc = legacy(version)
    with main.get_connection() as db:
        db.execute("UPDATE facts SET extraction_method = 'ocr'")
    facts = client.get('/facts').json()
    content = Path(doc['stored_path']).read_bytes()
    main.init_db()
    before = snapshot()
    main.init_db()
    assert snapshot() == before
    assert client.get('/facts').json() == facts
    response = client.get(f"/documents/{doc['id']}").json()
    assert response['stored_path'] == doc['stored_path']
    assert response['extraction_error'] == 'previous failure'
    assert client.get(f"/documents/{doc['id']}/source").content == content
    with main.get_connection() as db:
        assert db.execute('SELECT stored_path FROM documents').fetchone()[0] == Path(doc['stored_path']).name
        assert db.execute('PRAGMA user_version').fetchone()[0] == 3


@pytest.mark.parametrize('kind', ['outside', 'traversal', 'nested', 'relative', 'symlink', 'duplicate'])
def test_legacy_rejection_rolls_back(kind, tmp_path):
    doc = legacy()
    outside = tmp_path / 'sentinel.pdf'
    outside.write_bytes(b'unchanged')
    link = main.UPLOADS_DIR / 'link.pdf'
    link.symlink_to(outside)
    value = {'outside': str(outside), 'traversal': str(main.UPLOADS_DIR) + '/../outside.pdf', 'nested': str(main.UPLOADS_DIR / 'nested/a.pdf'), 'relative': 'a.pdf', 'symlink': str(link), 'duplicate': doc['stored_path']}[kind]
    with main.get_connection() as db:
        db.execute('INSERT INTO documents SELECT ?, filename, size_bytes, content_type, ?, created_at, status, extraction_error FROM documents LIMIT 1', ('bad', value))
    before = snapshot()
    with pytest.raises(ValueError, match='Cannot migrate document'):
        main.init_db()
    assert snapshot() == before
    assert outside.read_bytes() == b'unchanged'


def test_failure_rolls_back_schema_and_paths(monkeypatch):
    legacy()
    with main.get_connection() as db:
        db.execute('ALTER TABLE documents DROP COLUMN extraction_error')
        db.execute('ALTER TABLE facts DROP COLUMN extraction_method')
        db.execute('PRAGMA user_version = 1')
    before = snapshot()
    original = main.migrate_source_references
    def fail(db, uploads):
        original(db, uploads)
        raise RuntimeError('injected')
    monkeypatch.setattr(main, 'migrate_source_references', fail)
    with pytest.raises(RuntimeError, match='injected'):
        main.init_db()
    assert snapshot() == before


def test_future_schema_unchanged():
    with main.get_connection() as db:
        db.execute('PRAGMA user_version = 99')
    before = snapshot()
    with pytest.raises(ValueError, match='newer'):
        main.init_db()
    assert snapshot() == before


@pytest.mark.parametrize('value', ['/outside.pdf', '../outside.pdf', 'nested/a.pdf', 'a\\b.pdf', '', '.', '..', 'bad\0.pdf', 'link.pdf'])
def test_tampering_rejects_all_source_actions(value, tmp_path):
    doc = upload_pdf()
    sentinel = tmp_path / 'sentinel.pdf'
    sentinel.write_bytes(b'unchanged')
    (main.UPLOADS_DIR / 'link.pdf').symlink_to(sentinel)
    with main.get_connection() as db:
        db.execute('UPDATE documents SET stored_path = ?', (value,))
    before = snapshot()
    url = f"/documents/{doc['id']}"
    assert client.get(url).json()['stored_path'] == ''
    assert client.get(url + '/source').status_code == 404
    assert client.post(url + '/process').status_code == 409
    assert client.delete(url).status_code == 409
    assert snapshot() == before
    assert sentinel.read_bytes() == b'unchanged'


def test_missing_source_migrates_preserving_facts():
    doc = legacy()
    Path(doc['stored_path']).unlink()
    main.init_db()
    facts = client.get('/facts').json()
    url = f"/documents/{doc['id']}"
    assert client.get(url + '/source').status_code == 404
    assert client.post(url + '/process').status_code == 422
    assert client.get('/facts').json() == facts
    assert client.delete(url).status_code == 204


def test_unlink_failure_preserves_rows_and_retry(monkeypatch):
    doc = upload_pdf()
    before = snapshot()
    original = Path.unlink
    def fail(path, *args, **kwargs):
        if str(path) == doc['stored_path']:
            raise PermissionError('injected')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', fail)
    url = f"/documents/{doc['id']}"
    assert client.delete(url).status_code == 409
    assert snapshot() == before
    monkeypatch.setattr(Path, 'unlink', original)
    assert client.delete(url).status_code == 204
