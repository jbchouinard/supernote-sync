import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

import snsync.config
from snsync.supernote import SupernoteBrowserFile, walk_supernote_files, download_file, upload_file


def trash_file(path: Path, config=snsync.config.global_config):
    if config.trash_dir:
        new_path = (
            config.trash_dir
            / path.parent.relative_to(config.sync_dir)
            / f"{path.name}.deleted-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        new_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(new_path)
    else:
        path.unlink()


def sync_file_pull(
    snf: Optional[SupernoteBrowserFile],
    local_file: Optional[Path],
    config=snsync.config.global_config,
):
    if snf is None:
        if local_file is not None:
            logger.info("File {} not found on Supernote device, trashing file", local_file)
            trash_file(local_file, config)
    else:
        if local_file is not None:
            if config.check_file_size:
                if local_file.stat().st_size == snf.size:
                    logger.info("File {} already exists with the same size, skipping download", local_file)
                    return

        download_file(snf=snf, config=config)


def sync_file_push(
    snf: Optional[SupernoteBrowserFile],
    local_file: Optional[Path],
    config=snsync.config.global_config,
):
    if local_file is None:
        # Cannot delete files from Supernote device
        logger.info("File {} exists on device but not locally, nothing to do", snf.path)
        pass
    else:
        if snf is not None:
            if local_file.stat().st_size == snf.size:
                logger.info("File {} already exists with the same size", snf.path)
            else:
                logger.warning("Conflicting file exists on device {}", snf.path)
        else:
            logger.debug("File {} not found on Supernote device, uploading", local_file)
            upload_file(
                local_file=local_file,
                target_path=local_file.relative_to(config.sync_dir).as_posix(),
                config=config,
            )


def walk_local_files(config=snsync.config.global_config):
    for path in config.sync_dir.glob("**/*"):
        if path.is_file():
            yield path


def sync_files(config=snsync.config.global_config):
    sn_files = {snf.path.lstrip("/"): snf for snf in walk_supernote_files(config=config)}
    logger.debug("Found files on Supernote device: {}", sn_files)
    local_files = {p.relative_to(config.sync_dir).as_posix(): p for p in walk_local_files(config=config)}
    logger.debug("Found files on local device: {}", local_files)

    for pathstr in sn_files.keys() | local_files.keys():
        path = Path(pathstr)
        if path.suffix.lstrip(".").lower() not in config.sync_extensions:
            logger.debug("Skipping file {} (file extension not in sync_extensions)", path)
            continue
        first_dir = path.parts[0]
        if first_dir in config.pull_dirs:
            sync_file_pull(
                snf=sn_files.get(pathstr),
                local_file=local_files.get(pathstr),
                config=config,
            )
        if first_dir in config.push_dirs:
            sync_file_push(
                snf=sn_files.get(pathstr),
                local_file=local_files.get(pathstr),
                config=config,
            )
