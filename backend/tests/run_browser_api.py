"""Run the browser integration API with disposable storage and test-only CORS."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import uvicorn
from fastapi.middleware.cors import CORSMiddleware


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with TemporaryDirectory(prefix="factflow-browser-") as directory:
        # Set before importing app.main: import initializes the database.
        os.environ["FACTFLOW_DATA_DIR"] = directory
        from app.main import app

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:5190"],
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["*"],
        )
        uvicorn.run(app, host="127.0.0.1", port=8029)


if __name__ == "__main__":
    main()
