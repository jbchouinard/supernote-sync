from pathlib import Path
from typing import Annotated, FrozenSet, Iterable, Optional, Union

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings

from snsync.schema import PageSize


def strset(v: Union[str, Iterable[str]]) -> FrozenSet[str]:
    if isinstance(v, str):
        return frozenset(v.split(","))
    else:
        return frozenset(v)


StrSet = Annotated[FrozenSet[str], BeforeValidator(strset)]


class SupernoteConfig(BaseSettings):
    supernote_url: str
    supernote_device_name: str


class LoggingConfig(BaseSettings):
    log_file: Optional[Path] = None
    log_level: str = "WARNING"


class Config(SupernoteConfig, LoggingConfig):
    push_dirs: StrSet = "INBOX"
    pull_dirs: StrSet = "Note,Document,MyStyle,EXPORT,SCREENSHOT"
    sync_extensions: StrSet = "note,spd,spd-shm,spd-wal,pdf,epub,doc,txt,png,jpg,jpeg,webp"
    sync_interval: int = 60
    sync_dir: Path = Path("supernote/sync")
    trash_dir: Path = Path("supernote/trash")
    db_url: str = "sqlite:///supernote/db.sqlite"
    convert_to_pdf: bool = False
    force_reconvert: bool = False
    pdf_page_size: PageSize = PageSize.A5
    pdf_vectorize: bool = False


_global_config = None


def get_config():
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config
