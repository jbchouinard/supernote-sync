from pathlib import Path

from supernotelib.converter import PdfConverter
from supernotelib.parser import load_notebook

from snsync.schema import PageSize


def convert_notebook_to_pdf(
    path: Path, vectorize: bool = False, page_size: PageSize = PageSize.A5, strict=True
) -> bytes:
    notebook = load_notebook(path, policy="strict" if strict else "loose")
    converter = PdfConverter(notebook)
    converter.pagesize = page_size.size
    return converter.convert(page_number=-1, vectorize=vectorize)
