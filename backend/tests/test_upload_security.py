from fastapi.testclient import TestClient

from app.main import MAX_FILENAME_LENGTH, MAX_UPLOAD_BYTES, app

client = TestClient(app)


def test_upload_sanitizes_path_components_and_preserves_pdf_extension():
    response = client.post(
        "/documents",
        files={"file": ("../folder\\unsafe.pdf", b"not a real PDF", "application/pdf")},
    )

    assert response.status_code == 200, response.text
    document = response.json()
    assert document["filename"] == "unsafe.pdf"
    assert ".." not in document["stored_path"]


def test_upload_rejects_overlong_filename():
    filename = "a" * (MAX_FILENAME_LENGTH + 1) + ".pdf"
    response = client.post(
        "/documents",
        files={"file": (filename, b"not a real PDF", "application/pdf")},
    )

    assert response.status_code == 400, response.text


def test_upload_rejects_content_type_mismatch():
    response = client.post(
        "/documents",
        files={"file": ("document.pdf", b"not a real PDF", "application/octet-stream")},
    )

    assert response.status_code == 415, response.text


def test_upload_limit_constant_is_positive():
    assert MAX_UPLOAD_BYTES > 0
