from io import BytesIO
from pathlib import Path
import shutil
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from app.main import app
from tests.ocr_fixtures import CLAIM, COST, combine, scan
from tests.test_facts import make_pdf

client = TestClient(app)
requires_engine = pytest.mark.skipif(not shutil.which('tesseract'), reason='Install Tesseract with eng for OCR acceptance')


def upload(content):
    response = client.post('/documents', files={'file': ('scan.pdf', content, 'application/pdf')})
    assert response.status_code == 200, response.text
    return response.json()


def facts(document):
    return client.get('/facts', params={'document_id': document['id']}).json()['items']


@requires_engine
@pytest.mark.parametrize('case', ['clean', 'mixed', 'same_page', 'numbers', 'duplicate', 'text'])
def test_ocr_acceptance(case):
    image_pdf = scan()
    assert PdfReader(BytesIO(image_pdf)).pages[0].extract_text() == ''
    assert PdfReader(BytesIO(image_pdf)).pages[0].images.keys()
    cases = {
        'clean': (image_pdf, [(CLAIM, 1, 'ocr')]),
        'mixed': (combine(make_pdf(CLAIM), scan(COST)), [(CLAIM, 1, 'native'), (COST, 2, 'ocr')]),
        'same_page': (scan(COST, heading='Quarterly report'), [(COST, 1, 'ocr')]),
        'numbers': (scan('Revenue did not increase 20 percent.\nThe dose was 5 mg.'), [('Revenue did not increase 20 percent.', 1, 'ocr'), ('The dose was 5 mg.', 1, 'ocr')]),
        'duplicate': (combine(make_pdf(CLAIM), image_pdf), [(CLAIM, 1, 'native')]),
        'text': (combine(make_pdf(CLAIM), make_pdf(COST)), [(CLAIM, 1, 'native'), (COST, 2, 'native')]),
    }
    content, expected = cases[case]
    document = upload(content)
    assert document['status'] == 'processed', document
    assert sorted((f['claim'], f['source_page'], f['extraction_method']) for f in facts(document)) == sorted(expected)
    assert Path(document['stored_path']).read_bytes() == content
    assert client.get(f"/documents/{document['id']}/source").content == content
    assert client.post(f"/documents/{document['id']}/process").json()['extraction_error'] is None


@requires_engine
@pytest.mark.parametrize('variant', ['rotated', 'degraded'])
def test_challenging_scans(variant):
    document = upload(scan(rotate=90 if variant == 'rotated' else 0, degraded=variant == 'degraded'))
    if document['status'] == 'processed':
        assert [f['claim'] for f in facts(document)] == [CLAIM]
    else:
        assert document['extraction_error']
        assert facts(document) == []


def test_missing_engine(monkeypatch):
    monkeypatch.setenv('FACTFLOW_TESSERACT', '/nonexistent/factflow-tesseract')
    assert upload(make_pdf(CLAIM))['status'] == 'processed'
    document = upload(combine(make_pdf(CLAIM), scan()))
    assert document['status'] == 'extraction_failed'
    assert 'Tesseract' in document['extraction_error']
    assert facts(document) == []


@requires_engine
def test_missing_language_data(monkeypatch, tmp_path):
    monkeypatch.setenv('TESSDATA_PREFIX', str(tmp_path))
    document = upload(scan())
    assert document['status'] == 'extraction_failed'
    assert 'language data' in document['extraction_error']


def test_encrypted_and_page_budget():
    for encrypted in [True, False]:
        writer = PdfWriter()
        for _ in range(1 if encrypted else 41):
            writer.add_blank_page(width=72, height=72)
        if encrypted:
            writer.encrypt('secret')
        output = BytesIO()
        writer.write(output)
        document = upload(output.getvalue())
        assert document['status'] == 'extraction_failed'
        assert ('Encrypted' if encrypted else '40 page') in document['extraction_error']


def test_render_pixel_limit():
    writer = PdfWriter()
    writer.add_blank_page(width=5000, height=5000)
    output = BytesIO()
    writer.write(output)
    assert 'pixel' in upload(output.getvalue())['extraction_error']


def test_document_timeout_retains_previous_evidence(monkeypatch):
    from app import extraction
    document = upload(make_pdf(CLAIM))
    before = facts(document)
    monkeypatch.setattr(extraction, 'TOTAL_TIMEOUT', 0.001)
    response = client.post(f"/documents/{document['id']}/process")
    assert response.status_code == 422
    assert 'document limit' in response.json()['detail']
    for fact in before:
        fact['document_status'] = 'extraction_failed'
    assert facts(document) == before


def test_per_page_timeout(monkeypatch, tmp_path):
    from app import ocr_worker
    import subprocess
    monkeypatch.setattr(ocr_worker.shutil, 'which', lambda _: '/test/tesseract')
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired('tesseract', 20)
    monkeypatch.setattr(ocr_worker.subprocess, 'run', timeout)
    with pytest.raises(ValueError, match='per-page limit'):
        ocr_worker.recognize(tmp_path / 'image.png')


def test_renderer_failure(monkeypatch, tmp_path):
    from app import ocr_worker
    import pypdfium2
    path = tmp_path / 'scan.pdf'
    path.write_bytes(scan())
    def broken(*args, **kwargs):
        raise RuntimeError('renderer unavailable')
    monkeypatch.setattr(pypdfium2, 'PdfDocument', broken)
    with pytest.raises(ValueError, match='rendered'):
        ocr_worker.extract(str(path), str(tmp_path))
