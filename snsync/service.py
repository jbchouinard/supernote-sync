import sys
import time

from loguru import logger
from tabulate import tabulate

from snsync.config import Config, LoggingConfig, SupernoteConfig
from snsync.convert import convert_notebook_to_pdf
from snsync.db import create_tables
from snsync.supernote import SupernoteClient, SupernoteClientError
from snsync.sync import FileSyncChecker, FileSyncClient, SyncResult, make_sync_states_table


def setup_logging(config: LoggingConfig):
    if config.log_file:
        logger.remove()
        logger.add(config.log_file, level=config.log_level)
    else:
        logger.remove()
        logger.add(sys.stderr, level=config.log_level, format="<level>{message}</level>")


DEFAULT_DIRS = ["Note", "Document", "MyStyle", "EXPORT", "SCREENSHOT", "INBOX"]


def initialize(config: Config):
    create_tables(config)
    for dir_name in DEFAULT_DIRS:
        config.sync_dir.joinpath(dir_name).mkdir(parents=True, exist_ok=True)
    if config.trash_dir:
        config.trash_dir.mkdir(parents=True, exist_ok=True)


def run_check(config: Config):
    initialize(config)
    checker = FileSyncChecker(config)
    sync_states = checker.check_files()
    print(make_sync_states_table(sync_states))


def run_once(config: Config):
    initialize(config)
    checker = FileSyncChecker(config)
    syncer = FileSyncClient(config)
    if not syncer.sn_client.ping():
        logger.warning("Supernote device not reachable")
        return
    sync_states = list(checker.check_files())
    logger.debug("\n" + make_sync_states_table(sync_states))
    logger.info(f"Syncing {len(sync_states)} files...")
    for state in sync_states:
        result, local_meta = syncer.sync(state)
        if config.convert_to_pdf and local_meta and local_meta.path.suffix.lower() == ".note":
            pdf_path = local_meta.path.with_suffix(".converted.pdf")
            if result == SyncResult.DOWNLOADED or (
                result == SyncResult.OK and (not pdf_path.exists() or config.force_reconvert)
            ):
                logger.info(f"Converting {local_meta.path} to PDF...")
                pdf_bytes = convert_notebook_to_pdf(
                    local_meta.path,
                    page_size=config.pdf_page_size,
                    vectorize=config.pdf_vectorize,
                )
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                with pdf_path.open("wb") as f:
                    f.write(pdf_bytes)
    post_sync_states = checker.check_files()
    logger.debug("\n" + make_sync_states_table(post_sync_states))


def run_forever(config: Config):
    initialize(config)
    while True:
        try:
            run_once(config)
        except SupernoteClientError as e:
            logger.warning("Network error when connecting to device: {}", e)
        except Exception as e:
            logger.error("Error syncing files", exc_info=e)
        logger.info("Sleeping for {} seconds...", config.sync_interval)
        time.sleep(config.sync_interval)


def list_files(config: SupernoteConfig):
    client = SupernoteClient(config.supernote_url, config.supernote_device_name)
    files = list(client.list_files())
    data = [
        {
            "Device Name": f.device_name,
            "File Name": f.path,
            "Last Modified": f.last_modified,
            "Size": f.size,
        }
        for f in files
    ]
    print(tabulate(data, headers="keys"))
