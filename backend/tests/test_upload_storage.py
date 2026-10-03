import asyncio
from io import BytesIO
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import main, upload_storage
from tests.pdf_fixtures import make_pdf


class Reader:
    def __init__(self, content, failure=None):
        self.stream = BytesIO(content)
        self.requests = []
        self.failure = failure

    async def read(self, size):
        assert 0 < size <= upload_storage.CHUNK_BYTES
        self.requests.append(size)
        if self.failure and len(self.requests) == 2:
            raise self.failure
        return self.stream.read(size)


@pytest.mark.parametrize('size', [0, 1, main.MAX_UPLOAD_BYTES])
def test_bounded_copy_preserves_exact_bytes(tmp_path, size):
    tmp_path = tmp_path / 'copy'
    tmp_path.mkdir()
    data = b'x' * size
    reader = Reader(data)
    destination = tmp_path / 'source.pdf'
    assert asyncio.run(upload_storage.store_upload(reader, destination, main.MAX_UPLOAD_BYTES)) == size
    assert destination.read_bytes() == data
    assert list(tmp_path.iterdir()) == [destination]


def test_oversize_stops_at_limit_plus_one_without_publishing(tmp_path):
    tmp_path = tmp_path / 'copy'
    tmp_path.mkdir()
    reader = Reader(b'x' * (main.MAX_UPLOAD_BYTES + 100))
    with pytest.raises(upload_storage.UploadTooLarge):
        asyncio.run(upload_storage.store_upload(reader, tmp_path / 'source.pdf', main.MAX_UPLOAD_BYTES))
    assert reader.stream.tell() == main.MAX_UPLOAD_BYTES + 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('failure', [OSError('read failed'), asyncio.CancelledError()])
def test_interrupted_copy_removes_partial_file(tmp_path, failure):
    tmp_path = tmp_path / 'copy'
    tmp_path.mkdir()
    reader = Reader(b'x' * (upload_storage.CHUNK_BYTES * 2), failure)
    with pytest.raises(type(failure)):
        asyncio.run(upload_storage.store_upload(reader, tmp_path / 'source.pdf', main.MAX_UPLOAD_BYTES))
    assert list(tmp_path.iterdir()) == []


def test_publish_failure_removes_temporary_file(tmp_path, monkeypatch):
    tmp_path = tmp_path / 'copy'
    tmp_path.mkdir()
    def fail(*args):
        raise OSError('rename failed')
    monkeypatch.setattr(upload_storage.os, 'replace', fail)
    with pytest.raises(OSError):
        asyncio.run(upload_storage.store_upload(Reader(b'content'), tmp_path / 'source.pdf', 100))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("stage", ["connect", "commit"])
def test_api_registration_failure_cleans_source_and_retry_succeeds(monkeypatch, stage):
    client = TestClient(main.app)
    original = main.get_connection
    class FailingCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError('commit failed')

    def fail():
        if stage == 'commit':
            return sqlite3.connect(main.DB_PATH, factory=FailingCommit)
        raise sqlite3.OperationalError('database unavailable')
    monkeypatch.setattr(main, 'get_connection', fail)
    content = make_pdf('Revenue increased 20 percent.')
    response = client.post('/documents', files={'file': ('source.pdf', content, 'application/pdf')})
    assert response.status_code == 500
    assert list(main.UPLOADS_DIR.iterdir()) == []
    monkeypatch.setattr(main, 'get_connection', original)
    assert client.get('/documents').json()['total'] == 0
    response = client.post('/documents', files={'file': ('source.pdf', content, 'application/pdf')})
    assert response.status_code == 200
    assert response.json()['size_bytes'] == len(content)
    assert Path(response.json()['stored_path']).read_bytes() == content


def test_api_oversize_has_no_rows_or_files(monkeypatch):
    monkeypatch.setattr(main, 'MAX_UPLOAD_BYTES', 100)
    client = TestClient(main.app)
    response = client.post('/documents', files={'file': ('large.pdf', b'x' * 101, 'application/pdf')})
    assert response.status_code == 413
    assert client.get('/documents').json()['total'] == 0
    assert list(main.UPLOADS_DIR.iterdir()) == []


def test_write_failure_cleans_partial_and_api_reports_retry(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    original = upload_storage.NamedTemporaryFile

    @contextmanager
    def failing_output(*args, **kwargs):
        with original(*args, **kwargs) as output:
            def fail_write(chunk):
                output.write(chunk[:3])
                raise OSError('disk full')
            yield SimpleNamespace(name=output.name, write=fail_write)

    monkeypatch.setattr(upload_storage, 'NamedTemporaryFile', failing_output)
    client = TestClient(main.app)
    response = client.post('/documents', files={'file': ('source.pdf', b'content', 'application/pdf')})
    assert response.status_code == 500
    assert 'retry' in response.json()['detail'].lower()
    assert client.get('/documents').json()['total'] == 0
    assert list(main.UPLOADS_DIR.iterdir()) == []
