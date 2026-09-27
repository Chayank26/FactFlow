import os
from tempfile import TemporaryDirectory

import pytest


# Tests import app.main during collection, which initializes storage immediately.
# Redirect that initialization before any test module imports the application.
_collection_storage = TemporaryDirectory(prefix="factflow-test-collection-")
_previous_data_dir = os.environ.get("FACTFLOW_DATA_DIR")
os.environ["FACTFLOW_DATA_DIR"] = _collection_storage.name


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    from app import main

    data_dir = tmp_path / "data"
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "UPLOADS_DIR", data_dir / "uploads")
    monkeypatch.setattr(main, "DB_PATH", data_dir / "factlayer.db")
    main.init_db()
    yield data_dir


def pytest_unconfigure(config):
    if _previous_data_dir is None:
        os.environ.pop("FACTFLOW_DATA_DIR", None)
    else:
        os.environ["FACTFLOW_DATA_DIR"] = _previous_data_dir
    _collection_storage.cleanup()
