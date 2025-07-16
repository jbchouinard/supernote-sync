from __future__ import annotations

import datetime
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator, Optional, Tuple

from loguru import logger
from tabulate import tabulate

from snsync.config import ServiceConfig
from snsync.converter import Converter
from snsync.converter.note2pdf import NoteToPdfConverter
from snsync.converter.spd2png import SpdToPngConverter
from snsync.db import DbFileMeta, delete_file_meta, get_db_files_meta, record_file_action
from snsync.schema import LocalFileMeta, SupernoteFileMeta
from snsync.supernote import SupernoteClient


def list_synced_files(device_name, sync_dir, exts) -> Iterator[LocalFileMeta]:
    for path in sync_dir.glob("**/*"):
        if path.is_file():
            if path.suffix.lstrip(".") in exts:
                yield LocalFileMeta(
                    device_name=device_name,
                    sync_dir=sync_dir,
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


RE_CONVERTED = re.compile(r"\.converted\.[a-z]+$")


class FileSyncChecker:
    def __init__(
        self,
        sync_dir: str | Path,
        sync_extensions: Iterable[str],
        push_dirs: Iterable[str],
        pull_dirs: Iterable[str],
        snclient: SupernoteClient,
    ):
        self.snclient = snclient
        self.sync_dir = Path(sync_dir)
        self.sync_extensions = set(sync_extensions)
        self.push_dirs = set(push_dirs)
        self.pull_dirs = set(pull_dirs)

    @classmethod
    def from_config(cls, config: ServiceConfig) -> FileSyncChecker:
        return cls(
            sync_dir=config.sync_dir,
            sync_extensions=config.sync_extensions,
            push_dirs=config.push_dirs,
            pull_dirs=config.pull_dirs,
            snclient=SupernoteClient.from_config(config),
        )

    def sync_mode(self, file_key):
        device_name, path = file_key
        if RE_CONVERTED.search(path):
            return None
        if device_name == self.snclient.device_name:
            base_dir = Path(path).parts[0]
            if base_dir in self.pull_dirs:
                return SyncMode.PULL
            if base_dir in self.push_dirs:
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
        device_meta_by_key = {f.file_key: f for f in self.snclient.list_files()}
        local_meta_by_key = {
            f.file_key: f for f in list_synced_files(self.snclient.device_name, self.sync_dir, self.sync_extensions)
        }
        db_meta_by_key = {f.file_key: f for f in get_db_files_meta(self.snclient.device_name)}

        all_keys = set(device_meta_by_key.keys()) | set(local_meta_by_key.keys()) | set(db_meta_by_key.keys())
        for file_key in all_keys:
            if file_key[0] != self.snclient.device_name:
                logger.warning("File {} is not from device {}", file_key[1], self.snclient.device_name)
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
    def __init__(self, device_name: str, sync_dir: Path, snclient: SupernoteClient, trash_dir: Optional[Path] = None):
        self.device_name = device_name
        self.sync_dir = sync_dir
        self.trash_dir = trash_dir
        self.snclient = snclient

    @classmethod
    def from_config(cls, config: ServiceConfig) -> FileSyncClient:
        return cls(
            device_name=config.supernote_name,
            sync_dir=config.sync_dir,
            snclient=SupernoteClient.from_config(config),
            trash_dir=config.trash_dir,
        )

    def download(self, state: FileSyncState):
        assert state.device_meta, "cannot download file without device meta"
        target_path = self.sync_dir / state.file_key[1]
        self.snclient.download(state.device_meta, target_path)
        return LocalFileMeta(
            device_name=self.device_name,
            sync_dir=self.sync_dir,
            path=target_path,
        )

    def upload(self, state: FileSyncState):
        assert state.local_meta, "cannot upload file without local meta"
        target_path = state.file_key[1]
        self.snclient.upload(state.local_meta.path, target_path)

    def trash(self, state: FileSyncState):
        if state.mode == SyncMode.PUSH:
            logger.debug("Cannot remove files from Supernote device, do nothing")
            return
        assert state.local_meta, "cannot trash file without local meta"
        path = state.local_meta.path
        if not path.exists():
            return
        if self.trash_dir:
            new_path = (
                self.trash_dir
                / path.parent.relative_to(self.sync_dir)
                / f"{path.name}.deleted-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            new_path.parent.mkdir(parents=True, exist_ok=True)
            path.rename(new_path)
            logger.success("Moved {} to trash ({})", path, new_path)
        else:
            path.unlink()
            logger.success("Deleted {}", path)

    def sync(self, state: FileSyncState) -> Tuple[SyncResult, Optional[LocalFileMeta]]:
        if state.local_meta is None and state.device_meta is None:
            delete_file_meta(state.file_key)
            return SyncResult.DELETED, None
        if state.status == SyncStatus.OK:
            return SyncResult.OK, state.local_meta
        elif state.status == SyncStatus.CONFLICT:
            logger.warning("File {} is in conflict, skipping", state.file_key)
            return SyncResult.CONFLICT, state.local_meta
        elif state.mode == SyncMode.PULL and state.status in (SyncStatus.NEW, SyncStatus.STALE):
            local_meta = self.download(state)
            record_file_action(local_meta, "download")
            return SyncResult.DOWNLOADED, local_meta
        elif state.mode == SyncMode.PUSH and state.status == SyncStatus.NEW:
            self.upload(state)
            record_file_action(state.local_meta, "upload", self.device_name)
            return SyncResult.UPLOADED, state.local_meta
        elif state.mode == SyncMode.PULL and state.status == SyncStatus.DELETED:
            self.trash(state)
            delete_file_meta(state.file_key)
            return SyncResult.DELETED, state.local_meta
        else:
            logger.debug("Nothing to do for {} in state {} {}", state.file_key, state.status, state.mode)
            return None, None


class ConversionRunner:
    def __init__(self, output_dir: Path, tmp_dir: Path = Path("/tmp/supernote-sync/conversion")):
        self.converters_by_ext: dict[str, list[Converter]] = defaultdict(list)
        self.reconvert: dict[Converter, bool] = {}
        self.output_dir = output_dir
        self.tmp_dir = tmp_dir
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_config(cls, config: ServiceConfig) -> ConversionRunner:
        instance = cls(config.sync_dir)
        instance.add_converter(
            NoteToPdfConverter(vectorize=config.note_to_pdf_vectorize, page_size=config.note_to_pdf_page_size),
            config.note_to_pdf,
            config.note_to_pdf_reconvert,
        )
        instance.add_converter(SpdToPngConverter(), config.spd_to_png, config.spd_to_png_reconvert)
        return instance

    def add_converter(self, converter: Converter, enabled: bool, reconvert: bool):
        if enabled:
            for ext in converter.input_extensions():
                self.converters_by_ext[ext].append(converter)
            self.reconvert[converter] = reconvert

    def run_converters(self, result: SyncResult, local_meta: LocalFileMeta | None):
        if not local_meta:
            return
        converters = self.converters_by_ext.get(local_meta.path.suffix.lower().lstrip("."), [])
        for converter in converters:
            output_path = self.output_dir / local_meta.relative_path.with_suffix(
                f".converted.{converter.output_extension()}"
            )
            if result == SyncResult.DOWNLOADED or (
                result == SyncResult.OK and (not output_path.exists() or self.reconvert[converter])
            ):
                tmp_input_path = self.tmp_dir / local_meta.path.name
                shutil.copyfile(local_meta.path, tmp_input_path)
                try:
                    tmp_output_path = converter.convert(local_meta.path, self.tmp_dir)
                    shutil.copyfile(tmp_output_path, output_path)
                    tmp_output_path.unlink(output_path)
                    logger.success(
                        "Converted {} to {} using {}",
                        local_meta.path,
                        output_path,
                        converter.__class__.__qualname__,
                    )
                except Exception:
                    logger.exception("Error converting {} using {}", local_meta.path, converter.__class__.__qualname__)
                finally:
                    tmp_input_path.unlink()
