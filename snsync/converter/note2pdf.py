from pathlib import Path
from typing import Iterable

from supernotelib.converter import PdfConverter
from supernotelib.parser import load_notebook

from snsync.converter import Converter
from snsync.schema import PageSize


class NoteToPdfConverter(Converter):
    def __init__(self, vectorize: bool = False, page_size: PageSize = PageSize.A5, strict: bool = True):
        self.vectorize = vectorize
        self.page_size = page_size
        self.strict = strict

    @classmethod
    def input_extensions(cls) -> Iterable[str]:
        return ["note"]

    @classmethod
    def output_extension(cls) -> str:
        return "pdf"

    def convert(self, input_path: str | Path, output_dir: str | Path) -> Path:
        notebook = load_notebook(input_path, policy="strict" if self.strict else "loose")
        converter = PdfConverter(notebook)
        converter.pagesize = self.page_size.size
        pdf_bytes = converter.convert(page_number=-1, vectorize=self.vectorize)
        output_path = Path(output_dir) / input_path.with_suffix(".pdf").name
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        return output_path
