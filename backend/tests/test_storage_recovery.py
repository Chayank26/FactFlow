import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def probe(root, manifest, mode, success=True):
    result = subprocess.run([sys.executable, '-m', 'tests.recovery_fixture', mode, str(manifest)], cwd=BACKEND, env={**os.environ, 'FACTFLOW_DATA_DIR': str(root)}, capture_output=True, text=True)
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.mark.parametrize('scenario', ['relocated', 'same_path', 'missing', 'legacy_moved'])
def test_whole_directory_recovery_in_fresh_processes(tmp_path, scenario):
    original = tmp_path / 'a' / 'data'
    manifest = tmp_path / 'manifest.json'
    probe(original, manifest, 'seed')
    if scenario == 'legacy_moved':
        with sqlite3.connect(original / 'factlayer.db') as db:
            for identifier, name in db.execute('SELECT id, stored_path FROM documents').fetchall():
                db.execute('UPDATE documents SET stored_path = ? WHERE id = ?', (str(original / 'uploads' / name), identifier))
            db.execute('PRAGMA user_version = 2')
    archive = tmp_path / 'backup.tar.gz'
    with tarfile.open(archive, 'w:gz') as handle:
        handle.add(original, arcname='data')
    original.rename(tmp_path / 'retained-original')
    target = original if scenario == 'same_path' else tmp_path / 'b' / 'data'
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as handle:
        handle.extractall(target.parent, filter='data')
    if scenario == 'missing':
        shutil.rmtree(target / 'uploads')
        probe(target, manifest, 'missing')
    elif scenario == 'legacy_moved':
        before = (target / 'factlayer.db').read_bytes()
        result = probe(target, manifest, 'verify', success=False)
        assert result.returncode != 0 and 'original data root' in result.stderr
        assert (target / 'factlayer.db').read_bytes() == before
    else:
        probe(target, manifest, 'mutate')
    if scenario != 'same_path':
        assert not original.exists()
    # All mutations are isolated from the retained original directory.
    probe(tmp_path / 'retained-original', manifest, 'verify') if scenario != 'legacy_moved' else None
