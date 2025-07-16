from pathlib import Path
from typing import Annotated, Any, FrozenSet, Iterable, Optional, Union

from loguru import logger
from pydantic import AnyHttpUrl, BeforeValidator, Field, model_validator
from pydantic.networks import IPv4Address
from pydantic_settings import BaseSettings, SettingsConfigDict

from snsync.schema import PageSize


def strset(v: Union[str, Iterable[str]]) -> FrozenSet[str]:
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


StrSet = Annotated[FrozenSet[str], BeforeValidator(strset)]
MaybePath = Annotated[Optional[Path], BeforeValidator(empty_string_is_none)]
MaybeStr = Annotated[Optional[str], BeforeValidator(empty_string_is_none)]
MaybeIPv4 = Annotated[Optional[IPv4Address], BeforeValidator(empty_string_is_none)]


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(secrets_dir="/run/secrets", case_sensitive=False)


class SupernoteConfig(BaseConfig):
    supernote_ip: MaybeIPv4 = None
    supernote_url: AnyHttpUrl
    supernote_device_name: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def set_url_from_ip(cls, data: Any):
        if "supernote_url" not in data and "supernote_ip" in data:
            data["supernote_url"] = f"http://{data['supernote_ip']}:8089"
        return data


class LoggingConfig(BaseConfig):
    log_file: MaybeStr = None
    log_level: Annotated[LogLevel, BeforeValidator(to_log_level)] = "INFO"


class Config(SupernoteConfig, LoggingConfig):
    push_dirs: StrSet = "INBOX"
    pull_dirs: StrSet = "Note,Document,MyStyle,EXPORT,SCREENSHOT"
    sync_extensions: StrSet = "note,spd,spd-shm,spd-wal,pdf,epub,doc,txt,png,jpg,jpeg,webp"
    sync_interval: int = Field(gt=0, default=60)
    sync_dir: Path = Path("./supernote")
    trash_dir: MaybePath = None
    db_url: str = "sqlite:///supernote.db"
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
