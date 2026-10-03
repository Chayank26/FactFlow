import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Event

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile
from app import main
from app.admission import MutationGate
from tests.test_document_management import upload_pdf
from tests.pdf_fixtures import make_pdf


def upload(client):
    return client.post('/documents', files={'file': ('new.pdf', make_pdf('Revenue increased 20 percent.'), 'application/pdf')})


@pytest.mark.parametrize('operation', ['upload', 'process', 'delete'])
def test_busy_mutations_and_available_reads(monkeypatch, operation):
    client = TestClient(main.app)
    doc = upload_pdf()
    entered, release = Event(), Event()
    original_process, original_unlink = main.process_document, Path.unlink
    def paused_process(*args):
        entered.set()
        assert release.wait(10)
        return original_process(*args)
    def paused_unlink(path, *args, **kwargs):
        if str(path) == doc['stored_path']:
            entered.set()
            assert release.wait(10)
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(main, 'process_document', paused_process)
    if operation == 'delete':
        monkeypatch.setattr(Path, 'unlink', paused_unlink)
    url = f"/documents/{doc['id']}"
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: upload(client) if operation == 'upload' else client.post(url + '/process') if operation == 'process' else client.delete(url))
        try:
            assert entered.wait(5)
            before = sorted(path.name for path in main.UPLOADS_DIR.iterdir())
            count = client.get('/documents').json()['total']
            for response in [upload(client), client.post(url + '/process'), client.delete(url)]:
                assert response.status_code == 503
                assert response.headers['retry-after'] == '1'
            assert sorted(path.name for path in main.UPLOADS_DIR.iterdir()) == before
            assert client.get('/documents').json()['total'] == count
            for path in ['/health', '/documents', '/facts', '/comparisons', url, url + '/source']:
                assert client.get(path).status_code == 200
        finally:
            release.set()
        assert future.result(timeout=10).status_code == (204 if operation == 'delete' else 200)
    assert upload(client).status_code == 200


@pytest.mark.parametrize('failure', ['timeout', 'unexpected'])
def test_failed_worker_releases_slot(monkeypatch, failure):
    client = TestClient(main.app, raise_server_exceptions=False)
    doc = upload_pdf()
    original = main.process_document
    def fail(*args):
        if failure == 'timeout':
            raise HTTPException(status_code=422, detail='Document deadline exceeded')
        raise RuntimeError('unexpected worker failure')
    monkeypatch.setattr(main, 'process_document', fail)
    assert upload(client).status_code == (200 if failure == 'timeout' else 500)
    assert client.post(f"/documents/{doc['id']}/process").status_code == (422 if failure == 'timeout' else 500)
    monkeypatch.setattr(main, 'process_document', original)
    assert upload(client).status_code == 200


def test_cancelled_request_holds_slot_until_worker_completion():
    gate = MutationGate()
    entered, release, completed = Event(), Event(), Event()
    def worker():
        entered.set()
        assert release.wait(10)
        completed.set()
    async def scenario():
        async def request():
            with gate.reserve() as lease:
                await lease.run_sync(worker)
        task = asyncio.create_task(request())
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(HTTPException) as busy:
                with gate.reserve():
                    pass
            assert busy.value.status_code == 503
        finally:
            release.set()
        await asyncio.gather(*list(gate._workers))
        await asyncio.sleep(0)
        assert completed.is_set()
        with gate.reserve():
            pass
    asyncio.run(scenario())


def test_copy_cancellation_releases_slot(monkeypatch):
    async def cancelled(*args):
        raise asyncio.CancelledError()
    monkeypatch.setattr(main, 'store_upload', cancelled)
    file = UploadFile(BytesIO(b'content'), filename='source.pdf', headers=Headers({'content-type': 'application/pdf'}))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(main.upload_document(file))
    with main.mutation_gate.reserve():
        pass
    assert list(main.UPLOADS_DIR.iterdir()) == []
