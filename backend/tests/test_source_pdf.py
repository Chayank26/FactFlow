from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, get_connection
from tests.test_document_management import upload_pdf

client = TestClient(app)


def test_source_returns_original_pdf_inline_and_disappears_after_delete():
    document = upload_pdf()
    source = f"/documents/{document['id']}/source"
    response = client.get(source)
    assert response.status_code == 200
    assert response.content == Path(document['stored_path']).read_bytes()
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['content-disposition'].startswith('inline;')
    assert document['filename'] in response.headers['content-disposition']
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert client.delete(f"/documents/{document['id']}").status_code == 204
    assert client.get(source).status_code == 404


def test_source_missing_document_or_file_returns_not_found():
    assert client.get('/documents/missing/source').status_code == 404
    document = upload_pdf()
    Path(document['stored_path']).unlink()
    assert client.get(f"/documents/{document['id']}/source").status_code == 404


def test_source_rejects_path_outside_upload_directory(tmp_path):
    document = upload_pdf()
    outside = tmp_path / 'outside.pdf'
    outside.write_bytes(b'private content')
    with get_connection() as connection:
        connection.execute('UPDATE documents SET stored_path = ? WHERE id = ?', (str(outside), document['id']))
    response = client.get(f"/documents/{document['id']}/source")
    assert response.status_code == 404
    assert b'private content' not in response.content
