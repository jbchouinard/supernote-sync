import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional, Tuple

from loguru import logger
from tabulate import tabulate

from snsync.config import Config
from snsync.db import DbFileMeta, delete_file_meta, get_db_files_meta, record_file_action
from snsync.schema import LocalFileMeta, SupernoteFileMeta
from snsync.supernote import SupernoteClient


def list_synced_files(conf: Config) -> Iterator[LocalFileMeta]:
    for path in conf.sync_dir.glob("**/*"):
        if path.is_file():
            if path.suffix.lstrip(".") in conf.sync_extensions:
                yield LocalFileMeta(
                    device_name=conf.supernote_device_name,
                    sync_dir=conf.sync_dir,
                    path=path,
                )


class SyncMode(Enum):
    PUSH = "push"
    PULL = "pull"


class SyncStatus(Enum):
    OK = "ok"
    STALE = "stale"
    NEW = "new"
    DELETED = "deleted"
    CONFLICT = "conflict"


@dataclass
class FileSyncState:
    status: SyncStatus
    mode: SyncMode
    file_key: str
    device_meta: Optional[SupernoteFileMeta]
    local_meta: Optional[LocalFileMeta]
    db_meta: Optional[DbFileMeta]


class FileSyncChecker:
    def __init__(self, config: Config):
        self.config = config
        self.sn_client = SupernoteClient(config.supernote_url, config.supernote_device_name)

    def sync_mode(self, file_key):
        device_name, path = file_key
        if path.endswith(".converted.pdf"):
            return None
        if device_name == self.config.supernote_device_name:
            base_dir = Path(path).parts[0]
            if base_dir in self.config.pull_dirs:
                return SyncMode.PULL
            if base_dir in self.config.push_dirs:
                return SyncMode.PUSH
        return None

    def check_file_push(
        self,
        file_key: str,
        device_meta: Optional[SupernoteFileMeta],
        local_meta: Optional[LocalFileMeta],
        db_meta: Optional[DbFileMeta],
    ) -> FileSyncState:
        state = {
            "mode": SyncMode.PUSH,
            "file_key": file_key,
            "device_meta": device_meta,
            "local_meta": local_meta,
            "db_meta": db_meta,
        }
        if local_meta is None:
            return FileSyncState(SyncStatus.DELETED, **state)
        if device_meta is None:
            return FileSyncState(SyncStatus.NEW, **state)
        # Both local_meta and device_meta are not None
        file_changed = False
        if local_meta.size != device_meta.size:
            file_changed = True
        elif db_meta and local_meta.last_modified > db_meta.last_synced:
            file_changed = True
        elif db_meta and db_meta.md5 != local_meta.md5():
            file_changed = True
        if file_changed:
            # Files on device cannot be overwritten
            return FileSyncState(SyncStatus.CONFLICT, **state)
        else:
            return FileSyncState(SyncStatus.OK, **state)

    def check_file_pull(
        self,
        file_key: str,
        device_meta: Optional[SupernoteFileMeta],
        local_meta: Optional[LocalFileMeta],
        db_meta: Optional[DbFileMeta],
    ) -> FileSyncState:
        state = {
            "mode": SyncMode.PULL,
            "file_key": file_key,
            "device_meta": device_meta,
            "local_meta": local_meta,
            "db_meta": db_meta,
        }
        if device_meta is None:
            return FileSyncState(SyncStatus.DELETED, **state)
        if local_meta is None:
            return FileSyncState(SyncStatus.NEW, **state)
        # Both local_meta and device_meta are not None
        if db_meta and db_meta.md5 != local_meta.md5():
            return FileSyncState(SyncStatus.CONFLICT, **state)
        file_changed = False
        if local_meta.size != device_meta.size:
            file_changed = True
        elif db_meta and device_meta.last_modified > db_meta.last_synced:
            file_changed = True
        if file_changed:
            return FileSyncState(SyncStatus.STALE, **state)
        else:
            return FileSyncState(SyncStatus.OK, **state)

    def check_files(self) -> Iterator[FileSyncState]:
        device_meta_by_key = {f.file_key: f for f in self.sn_client.list_files()}
        local_meta_by_key = {f.file_key: f for f in list_synced_files(self.config)}
        db_meta_by_key = {f.file_key: f for f in get_db_files_meta(self.config)}

        all_keys = set(device_meta_by_key.keys()) | set(local_meta_by_key.keys()) | set(db_meta_by_key.keys())
        for file_key in all_keys:
            if file_key[0] != self.config.supernote_device_name:
                logger.warning("File {} is not from device {}", file_key[1], self.config.supernote_device_name)
                continue
            mode = self.sync_mode(file_key)
            if mode == SyncMode.PULL:
                yield self.check_file_pull(
                    file_key=file_key,
                    device_meta=device_meta_by_key.get(file_key),
                    local_meta=local_meta_by_key.get(file_key),
                    db_meta=db_meta_by_key.get(file_key),
                )
            elif mode == SyncMode.PUSH:
                yield self.check_file_push(
                    file_key=file_key,
                    device_meta=device_meta_by_key.get(file_key),
                    local_meta=local_meta_by_key.get(file_key),
                    db_meta=db_meta_by_key.get(file_key),
                )


def make_sync_states_table(states: list[FileSyncState]):
    data = sorted(
        [
            {
                "Device Name": s.file_key[0],
                "File Name": s.file_key[1],
                "Mode": s.mode.value.upper(),
                "Status": s.status.value.upper(),
                "Device Size": s.device_meta.size if s.device_meta else -1,
                "Local Size": s.local_meta.size if s.local_meta else -1,
                "Last Synced": s.db_meta.last_synced if s.db_meta else "",
                "Last Sync Action": s.db_meta.last_sync_action if s.db_meta else "",
            }
            for s in states
        ],
        key=lambda x: (x["Mode"], x["Device Name"], x["File Name"]),
    )
    return tabulate(data, headers="keys")


class SyncResult(Enum):
    OK = "ok"
    CONFLICT = "conflict"
    DOWNLOADED = "downloaded"
    UPLOADED = "uploaded"
    DELETED = "deleted"


class FileSyncClient:
    def __init__(self, config: Config):
        self.config = config
        self.sn_client = SupernoteClient(config.supernote_url, config.supernote_device_name)

    def download(self, state: FileSyncState):
        assert state.device_meta, "cannot download file without device meta"
        target_path = self.config.sync_dir / state.file_key[1]
        self.sn_client.download(state.device_meta, target_path)
        return LocalFileMeta(
            device_name=self.config.supernote_device_name,
            sync_dir=self.config.sync_dir,
            path=target_path,
        )

    def upload(self, state: FileSyncState):
        assert state.local_meta, "cannot upload file without local meta"
        target_path = state.file_key[1]
        self.sn_client.upload(state.local_meta.path, target_path)

    def trash(self, state: FileSyncState):
        if state.mode == SyncMode.PUSH:
            logger.debug("Cannot remove files from Supernote device, do nothing")
            return
        assert state.local_meta, "cannot trash file without local meta"
        path = state.local_meta.path
        if not path.exists():
            return
        if self.config.trash_dir:
            new_path = (
                self.config.trash_dir
                / path.parent.relative_to(self.config.sync_dir)
                / f"{path.name}.deleted-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            new_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Moving {} to trash ({})", path, new_path)
            path.rename(new_path)
        else:
            logger.info("Deleting {}", path)
            path.unlink()

    def sync(self, state: FileSyncState) -> Tuple[SyncResult, Optional[LocalFileMeta]]:
        if state.local_meta is None and state.device_meta is None:
            delete_file_meta(state.file_key, self.config)
            return SyncResult.DELETED, None
        if state.status == SyncStatus.OK:
            return SyncResult.OK, state.local_meta
        elif state.status == SyncStatus.CONFLICT:
            logger.warning("File {} is in conflict, skipping", state.file_key)
            return SyncResult.CONFLICT, state.local_meta
        elif state.mode == SyncMode.PULL and state.status in (SyncStatus.NEW, SyncStatus.STALE):
            local_meta = self.download(state)
            record_file_action(local_meta, "download", self.config)
            return SyncResult.DOWNLOADED, local_meta
        elif state.mode == SyncMode.PUSH and state.status == SyncStatus.NEW:
            self.upload(state)
            record_file_action(state.local_meta, "upload", self.config)
            return SyncResult.UPLOADED, state.local_meta
        elif state.mode == SyncMode.PULL and state.status == SyncStatus.DELETED:
            self.trash(state)
            delete_file_meta(state.file_key, self.config)
            return SyncResult.DELETED, state.local_meta
        else:
            logger.debug("Nothing to do for {} in state {} {}", state.file_key, state.status, state.mode)
            return None, None
