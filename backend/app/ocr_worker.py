"""Disposable extraction process: native text or English OCR, never edits input."""
import csv
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

from pypdf import PdfReader

MAX_PAGES = 40
MAX_PIXELS = 12_000_000
PAGE_TIMEOUT = 20
DPI = 300


def recognize(image_path):
    engine = shutil.which(os.environ.get('FACTFLOW_TESSERACT', 'tesseract'))
    if not engine:
        raise ValueError('OCR requires Tesseract with English language data; install it and retry.')
    try:
        result = subprocess.run(
            [engine, str(image_path), 'stdout', '-l', 'eng', '--psm', '6', 'tsv'],
            capture_output=True, text=True, timeout=PAGE_TIMEOUT,
            env={**os.environ, 'OMP_THREAD_LIMIT': '1'},
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError('OCR exceeded the 20 second per-page limit.') from error
    if result.returncode:
        raise ValueError('OCR engine failed. Verify Tesseract and its English language data.')
    lines = {}
    scores = []
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter='\t', quoting=csv.QUOTE_NONE):
        text = (row.get('text') or '').strip()
        if row.get('level') != '5' or not text:
            continue
        score = float(row['conf'])
        scores.append(score)
        key = (row['block_num'], row['par_num'], row['line_num'])
        lines.setdefault(key, []).append(text)
    if not scores or min(scores) < 40 or sum(scores) / len(scores) < 80:
        raise ValueError('OCR could not read this page reliably. Try a clearer, upright scan.')
    return '\n'.join(' '.join(words) for words in lines.values())


def extract(path, scratch):
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported. Upload an unencrypted copy.')
    if len(reader.pages) > MAX_PAGES:
        raise ValueError('The PDF exceeds the 40 page processing limit.')
    pages = []
    rendered = None
    try:
        for index, page in enumerate(reader.pages):
            native = page.extract_text() or ''
            # Including image-bearing text pages prevents a heading from hiding a scan.
            if native.strip() and not page.images.keys():
                pages.append({'text': native, 'method': 'native'})
                continue
            try:
                import pypdfium2 as pdfium
                if rendered is None:
                    rendered = pdfium.PdfDocument(path)
                render_page = rendered[index]
                try:
                    width, height = render_page.get_size()
                    scale = DPI / 72
                    if math.ceil(width * scale) * math.ceil(height * scale) > MAX_PIXELS:
                        raise ValueError('The PDF page exceeds the 12 million pixel rendering limit.')
                    bitmap = render_page.render(scale=scale)
                    try:
                        image = bitmap.to_pil()
                        image_path = Path(scratch) / 'page.png'
                        image.save(image_path)
                        image.close()
                    finally:
                        bitmap.close()
                finally:
                    render_page.close()
                text = recognize(image_path)
            except ImportError as error:
                raise ValueError('OCR rendering requires pypdfium2 and Pillow.') from error
            except ValueError:
                raise
            except Exception as error:
                raise ValueError('The PDF page could not be rendered for OCR.') from error
            pages.append({'text': text, 'method': 'ocr'})
    finally:
        if rendered is not None:
            rendered.close()
    return pages


if __name__ == '__main__':
    try:
        payload = {'pages': extract(sys.argv[1], sys.argv[2])}
    except ValueError as error:
        payload = {'error': str(error)}
    except Exception:
        payload = {'error': 'The PDF could not be read. Check that it is a valid, unencrypted PDF.'}
    print(json.dumps(payload))
