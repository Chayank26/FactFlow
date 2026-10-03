"""Local OCR benchmark; generated inputs and extraction never touch app storage."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.extraction import extract_pages
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version
from pypdf import PdfReader, PdfWriter
import importlib.metadata


def fixture(pages):
    image = Image.new('RGB', (2550, 3300), 'white')
    ImageDraw.Draw(image).multiline_text((150, 250), 'Revenue increased 20 percent.\nCosts decreased 5 percent.', font=ImageFont.load_default(size=64), fill='black', spacing=40)
    buffer = BytesIO()
    image.save(buffer, format='PDF', resolution=300)
    reader = PdfReader(BytesIO(buffer.getvalue()))
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_page(reader.pages[0])
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def run(pages):
    with TemporaryDirectory(prefix='factflow-benchmark-') as directory:
        source = Path(directory) / 'scan.pdf'
        source.write_bytes(fixture(pages))
        start = perf_counter()
        result = extract_pages(source)
        seconds = perf_counter() - start
        assert len(result) == pages
        assert all(page['method'] == 'ocr' and page['text'] == 'Revenue increased 20 percent.\nCosts decreased 5 percent.' for page in result)
        # Each scenario runs in a fresh Python process. This reports the largest
        # child-process peak, not the sum of simultaneously resident processes.
        peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        mib = peak / (1024 ** 2 if sys.platform == 'darwin' else 1024)
        return {'pages': pages, 'seconds': round(seconds, 3), 'seconds_per_page_average': round(seconds/pages, 3), 'largest_child_peak_mib': round(mib, 1), 'bytes': source.stat().st_size}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.scenario:
        print(json.dumps(run(args.scenario)))
    else:
        results = []
        for pages in [1, 10, 40]:
            for trial in [1, 2]:
                completed = subprocess.run([sys.executable, __file__, '--scenario', str(pages)], capture_output=True, text=True, check=True, timeout=110)
                row = json.loads(completed.stdout)
                row['trial'] = trial
                results.append(row)
                print(json.dumps(row), flush=True)
        report = {'machine': platform.platform(), 'processor': platform.machine(), 'python': platform.python_version(), 'tesseract': subprocess.check_output(['tesseract', '--version'], text=True).splitlines()[0], 'pypdfium2': importlib.metadata.version('pypdfium2'), 'pillow': pillow_version, 'dpi': 300, 'language': 'eng', 'pixels_per_page': 2550*3300, 'targets_seconds': {'1': 5, '10': 10, '40': 30}, 'results': results}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2)+'\n')
