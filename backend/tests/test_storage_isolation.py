from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_facts import make_pdf


@pytest.mark.parametrize("run", [1, 2])
def test_each_test_starts_empty_and_stores_uploads_in_temporary_directory(isolated_storage, run):
    with TestClient(app) as client:
        assert client.get("/documents").json()["items"] == []
        assert client.get("/facts").json()["total"] == 0
        response = client.post(
            "/documents",
            files={"file": (f"isolated-{run}.pdf", make_pdf("Revenue increased 20 percent."), "application/pdf")},
        )
        assert response.status_code == 200, response.text
        document = response.json()
        assert document["status"] == "processed"
        stored_path = Path(document["stored_path"])
        assert stored_path.parent == isolated_storage / "uploads"
        assert stored_path.is_file()
        assert len(client.get("/documents").json()["items"]) == 1
        assert client.get("/facts").json()["total"] == 1
