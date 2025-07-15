import sys
import time

from loguru import logger

from snsync.sync import sync_files


def initialize(config):
    if config.log_file:
        logger.remove()
        logger.add(config.log_file, level=config.log_level)
    else:
        logger.remove()
        logger.add(sys.stderr, level=config.log_level)

    logger.info("Initializing supernote-sync with config: {}", config)
    config.sync_dir.mkdir(parents=True, exist_ok=True)
    if config.trash_dir:
        config.trash_dir.mkdir(parents=True, exist_ok=True)


def run(config):
    initialize(config)
    while True:
        try:
            sync_files(config)
        except Exception as e:
            logger.error("Error syncing files: {}", e)
        time.sleep(config.sync_interval)
