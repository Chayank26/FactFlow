"""Bound PDF parsing/rendering/OCR in an isolated process group (macOS/Linux)."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory

TOTAL_TIMEOUT = 90


def extract_pages(path):
    with TemporaryDirectory(prefix='factflow-ocr-') as scratch:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name('ocr_worker.py')), str(path), scratch],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
        try:
            stdout, _ = process.communicate(timeout=TOTAL_TIMEOUT)
        except subprocess.TimeoutExpired as error:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ValueError('PDF processing exceeded the 90 second document limit.') from error
        if process.returncode:
            raise ValueError('The PDF extraction process failed.')
        result = json.loads(stdout)
        if 'error' in result:
            raise ValueError(result['error'])
        return result['pages']
