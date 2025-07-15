from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


def split_list(v: Union[str, List[str]]) -> List[str]:
    if isinstance(v, str):
        return v.split(",")
    return v


class ServiceConfig(BaseSettings):
    supernote_address: str
    supernote_port: int = 8089
    push_dirs: List[str] = ["INBOX"]
    pull_dirs: List[str] = ["Note", "Document", "EXPORT", "SCREENSHOT", "MyStyle"]
    sync_extensions: List[str] = ["note", "spd", "pdf", "epub", "png", "doc", "txt"]
    sync_interval: int = 60
    sync_dir: Path = Path("./supernote/sync")
    trash_dir: Path = Path("./supernote/trash")
    check_file_size: bool = True
    log_file: Optional[Path] = None
    log_level: str = "INFO"

    @field_validator("push_dirs", mode="before")
    def split_push_dirs(cls, v):
        return split_list(v)

    @field_validator("pull_dirs", mode="before")
    def split_pull_dirs(cls, v):
        return split_list(v)

    @field_validator("sync_extensions", mode="before")
    def split_sync_extensions(cls, v):
        return split_list(v)

    @property
    def supernote_url(self):
        return f"http://{self.supernote_address}:{self.supernote_port}"


global_config = ServiceConfig()
