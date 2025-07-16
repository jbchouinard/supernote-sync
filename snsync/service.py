import sys
import time
from pathlib import Path

from loguru import logger
from tabulate import tabulate

from snsync.config import LoggingConfig, ServiceConfig, SupernoteConfig
from snsync.db import create_tables
from snsync.supernote import SupernoteClient, SupernoteClientError
from snsync.sync import ConversionRunner, FileSyncChecker, FileSyncClient, make_sync_states_table


def setup_logging(config: LoggingConfig):
    if not config.log_file or config.log_file.lower() in ("stdout", "-"):
        log_file = sys.stdout
    elif config.log_file.lower == "stderr":
        log_file = sys.stderr
    else:
        log_file = Path(config.log_file)

    logger.remove()
    if log_file is sys.stdout:
        logger.add(sys.stdout, level=config.log_level, format="<level>{message}</level>")
    else:
        logger.add(log_file, level=config.log_level)


DEFAULT_DIRS = ["Note", "Document", "MyStyle", "EXPORT", "SCREENSHOT", "INBOX"]


def initialize(config: ServiceConfig):
    create_tables()
    for dir_name in DEFAULT_DIRS:
        config.sync_dir.joinpath(dir_name).mkdir(parents=True, exist_ok=True)
    if config.trash_dir:
        config.trash_dir.mkdir(parents=True, exist_ok=True)


def run_check(config: ServiceConfig):
    initialize(config)
    checker = FileSyncChecker.from_config(config)
    sync_states = checker.check_files()
    print(make_sync_states_table(sync_states))


def _run_once(checker: FileSyncChecker, syncer: FileSyncClient, converter: ConversionRunner):
    if not syncer.snclient.ping():
        logger.info("Supernote device not reachable")
        return
    sync_states = list(checker.check_files())
    logger.debug("\n" + make_sync_states_table(sync_states))
    logger.info(f"Syncing {len(sync_states)} files...")
    sync_results = [syncer.sync(state) for state in sync_states]
    for result, local_meta in sync_results:
        converter.run_converters(result, local_meta)
    post_sync_states = checker.check_files()
    logger.debug("\n" + make_sync_states_table(post_sync_states))


def run_once(config: ServiceConfig):
    initialize(config)
    checker = FileSyncChecker.from_config(config)
    syncer = FileSyncClient.from_config(config)
    converter = ConversionRunner.from_config(config)
    _run_once(checker, syncer, converter)


def run_forever(config: ServiceConfig):
    initialize(config)
    checker = FileSyncChecker.from_config(config)
    syncer = FileSyncClient.from_config(config)
    converter = ConversionRunner.from_config(config)
    while True:
        try:
            _run_once(checker, syncer, converter)
        except SupernoteClientError as e:
            logger.warning("Network error when connecting to device: {}", e)
        except Exception:
            logger.exception("Error syncing files")
        logger.info("Sleeping for {} seconds...", config.sync_interval)
        time.sleep(config.sync_interval)


def list_files(config: SupernoteConfig):
    client = SupernoteClient.from_config(config)
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
