"""Synthetic scan corpus using Pillow's bundled Aileron font at 300 DPI."""
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from tests.pdf_fixtures import make_pdf

CLAIM = 'Revenue increased 20 percent.'
COST = 'Costs decreased 5 percent.'


def scan(text=CLAIM, heading=None, rotate=0, degraded=False):
    image = Image.new('RGB', (1800, 900), 'white')
    ImageDraw.Draw(image).multiline_text((100, 220), text, font=ImageFont.load_default(size=48), fill='black', spacing=30)
    if degraded:
        image = image.resize((900, 450)).resize((1800, 900)).rotate(2, fillcolor='white')
    if rotate:
        image = image.rotate(rotate, expand=True, fillcolor='white')
    output = BytesIO()
    image.save(output, format='PDF', resolution=300)
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(output.getvalue())))
    page = writer.pages[0]
    if heading:
        overlay = PdfReader(BytesIO(make_pdf(heading))).pages[0]
        contents = DecodedStreamObject()
        contents.set_data(f'BT /F1 12 Tf 24 185 Td ({heading}) Tj ET'.encode())
        overlay[NameObject('/Contents')] = contents
        page.merge_page(overlay)
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def combine(*pdfs):
    writer = PdfWriter()
    for content in pdfs:
        writer.append(PdfReader(BytesIO(content)))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


if __name__ == '__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(scan())
