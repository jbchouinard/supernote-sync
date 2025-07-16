from pathlib import Path
from typing import Iterable

from sn2md.importers.atelier import spd_to_png

from snsync.converter import Converter


class SpdToPngConverter(Converter):
    @classmethod
    def input_extensions(cls) -> Iterable[str]:
        return ["spd"]

    @classmethod
    def output_extension(cls) -> str:
        return "png"

    def convert(self, input_path: str | Path, output_dir: str | Path) -> Path:
        spd_to_png(str(input_path), str(output_dir))
        return Path(output_dir) / Path(input_path).with_suffix(".png").name
