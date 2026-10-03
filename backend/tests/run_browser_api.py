"""Run the browser integration API with disposable storage and test-only CORS."""
import os
from pathlib import Path
import sys
import subprocess
import tarfile
from tempfile import TemporaryDirectory

import uvicorn
from fastapi.middleware.cors import CORSMiddleware


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with TemporaryDirectory(prefix="factflow-browser-") as directory:
        # Set before importing app.main: import initializes the database.
        root = Path(directory)
        original = root / 'original' / 'data'
        manifest = root / 'manifest.json'
        env = {**os.environ, 'FACTFLOW_DATA_DIR': str(original)}
        subprocess.run([sys.executable, '-m', 'tests.recovery_fixture', 'seed', str(manifest)], cwd=Path(__file__).resolve().parents[1], env=env, check=True)
        archive = root / 'backup.tar.gz'
        with tarfile.open(archive, 'w:gz') as handle:
            handle.add(original, arcname='data')
        original.rename(root / 'retained-original')
        restored = root / 'restored'
        restored.mkdir()
        with tarfile.open(archive) as handle:
            handle.extractall(restored, filter='data')
        os.environ["FACTFLOW_DATA_DIR"] = str(restored / 'data')
        subprocess.run([sys.executable, '-m', 'tests.recovery_fixture', 'verify', str(manifest)], cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(), check=True)
        from app import main as application
        from tests.contention_control import install
        install(application)
        app = application.app

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:5190"],
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["*"],
        )
        uvicorn.run(app, host="127.0.0.1", port=8029)


if __name__ == "__main__":
    main()
