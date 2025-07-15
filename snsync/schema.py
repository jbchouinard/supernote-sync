import datetime
import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import unquote_plus

import reportlab.lib.pagesizes as pagesizes


@dataclass
class SupernoteFileMeta:
    device_name: str
    is_dir: bool
    path: str
    ext: str
    last_modified: datetime.datetime
    size: int

    @property
    def file_key(self):
        return (self.device_name, self.path.lstrip("/"))

    def is_valid(self):
        return self.path and (self.ext is not None) and (self.size is not None) and self.last_modified

    @classmethod
    def from_json_data(cls, device_name, obj):
        return cls(
            device_name=device_name,
            is_dir=obj.get("isDirectory", False),
            path=unquote_plus(obj.get("uri")),
            ext=obj.get("extension"),
            last_modified=datetime.datetime.strptime(obj.get("date"), "%Y-%m-%d %H:%M"),
            size=obj.get("size"),
        )


@dataclass
class LocalFileMeta:
    device_name: str
    sync_dir: Path
    path: Path

    @property
    def is_file(self) -> bool:
        return self.path.is_file()

    @property
    def is_dir(self) -> bool:
        return self.path.is_dir()

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    @property
    def last_modified(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.path.stat().st_mtime)

    @property
    def file_key(self):
        return (self.device_name, self.path.relative_to(self.sync_dir).as_posix().lstrip("/"))

    def md5(self) -> bytes:
        if not self.is_file:
            raise ValueError("Cannot compute md5 sum of non-file")
        return hashlib.md5(self.path.read_bytes()).digest()


PAGE_SIZES = {
    "A0": pagesizes.A0,
    "A1": pagesizes.A1,
    "A2": pagesizes.A2,
    "A3": pagesizes.A3,
    "A4": pagesizes.A4,
    "A5": pagesizes.A5,
    "A6": pagesizes.A6,
    "A7": pagesizes.A7,
    "A8": pagesizes.A8,
    "A9": pagesizes.A9,
    "A10": pagesizes.A10,
}


class PageSize(Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"
    A6 = "A6"
    A7 = "A7"
    A8 = "A8"
    A9 = "A9"
    A10 = "A10"

    @property
    def size(self):
        return PAGE_SIZES[self.value]
