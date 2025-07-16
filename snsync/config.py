from pathlib import Path
from typing import Annotated, FrozenSet, Iterable, Optional

from loguru import logger
from pydantic import AliasChoices, BeforeValidator, Field
from pydantic.networks import IPv4Address
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from snsync.schema import PageSize


def strset(v: str | Iterable[str]) -> FrozenSet[str]:
    if isinstance(v, str):
        return frozenset(v.split(","))
    else:
        return frozenset(v)


def empty_string_is_none(v: str) -> Optional[str]:
    if v == "":
        return None
    return v


class LogLevel(str):
    def __init__(self, value: str):
        self.level = logger.level(value)


def to_log_level(v: str) -> LogLevel:
    if isinstance(v, LogLevel):
        return v
    return LogLevel(v)


StrSet = Annotated[FrozenSet[str], BeforeValidator(strset), NoDecode]
MaybePath = Annotated[Optional[Path], BeforeValidator(empty_string_is_none)]
MaybeStr = Annotated[Optional[str], BeforeValidator(empty_string_is_none)]


def secrets_dir() -> Path | None:
    for p in [Path("/run/secrets"), Path("/var/run/secrets")]:
        if p.exists():
            return p
    return None


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(secrets_dir=secrets_dir(), case_sensitive=False)


class DatabaseConfig(BaseConfig):
    db_url: str = "sqlite:///supernote.db"


class LoggingConfig(BaseConfig):
    log_file: MaybeStr = None
    log_level: Annotated[LogLevel, BeforeValidator(to_log_level)] = "INFO"


class SupernoteConfig(BaseConfig):
    ip: IPv4Address = Field(validation_alias=AliasChoices("ip", "supernote_ip"))
    port: int = Field(validation_alias=AliasChoices("port", "supernote_port"), gt=0, lte=65535, default=8089)
    name: str = Field(validation_alias=AliasChoices("name", "supernote_name"), min_length=1)

    @property
    def supernote_url(self):
        return f"http://{self.ip}:{self.port}"

    @property
    def supernote_name(self):
        return self.name


class ConvertNoteToPdfConfig(BaseConfig):
    note_to_pdf: bool = True
    note_to_pdf_page_size: PageSize = PageSize.A5
    note_to_pdf_vectorize: bool = False
    note_to_pdf_reconvert: bool = False


class ConvertSpdToPngConfig(BaseConfig):
    spd_to_png: bool = True
    spd_to_png_reconvert: bool = False


class SyncConfig(BaseConfig):
    push_dirs: StrSet = "INBOX"
    pull_dirs: StrSet = "Note,Document,MyStyle,EXPORT,SCREENSHOT"
    sync_extensions: StrSet = "note,spd,spd-shm,spd-wal,pdf,epub,doc,txt,png,jpg,jpeg,webp"
    sync_interval: int = Field(gt=0, default=60)
    sync_dir: Path = Path("./supernote")
    trash_dir: MaybePath = None


class ServiceConfig(
    SupernoteConfig,
    LoggingConfig,
    DatabaseConfig,
    SyncConfig,
    ConvertNoteToPdfConfig,
    ConvertSpdToPngConfig,
):
    pass


_global_config = None


def get_config() -> ServiceConfig:
    global _global_config
    if _global_config is None:
        _global_config = ServiceConfig()
    return _global_config
