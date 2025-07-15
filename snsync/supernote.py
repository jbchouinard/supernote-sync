import datetime
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Union
from urllib.parse import unquote

import requests
from loguru import logger

import snsync.config

RE_JSON = re.compile(r"const json = '({[^']+})'")


class FetchError(Exception):
    pass


def get_supernote_data(path="/", config=snsync.config.global_config):
    url = f"{config.supernote_url}{path}"
    try:
        logger.debug("Fetching {}", url)
        contents = requests.get(url).text
    except requests.exceptions.RequestException as e:
        raise FetchError(f"Error fetching {url}: {e}") from e

    json_str = RE_JSON.search(contents).group(1)
    if not json_str:
        raise FetchError("JSON not found in page")
    return json.loads(json_str)


@dataclass
class SupernoteBrowserFile:
    is_dir: bool
    path: str
    ext: str
    timestamp: datetime.datetime
    size: int

    def is_valid(self):
        return self.path and (self.ext is not None) and (self.size is not None) and self.timestamp

    @classmethod
    def from_json(cls, obj):
        return cls(
            is_dir=obj.get("isDirectory", False),
            path=unquote(obj.get("uri")),
            ext=obj.get("extension"),
            timestamp=datetime.datetime.strptime(obj.get("date"), "%Y-%m-%d %H:%M"),
            size=obj.get("size"),
        )


def walk_supernote_files(dirs=["/"], config=snsync.config.global_config) -> Iterator[SupernoteBrowserFile]:
    while dirs:
        path = dirs.pop(0)
        data = get_supernote_data(path, config)
        file_list = data.get("fileList", [])
        for file_obj in file_list:
            logger.debug("Got file {}", file_obj)
            is_dir = file_obj.get("isDirectory", False)
            file_uri = file_obj.get("uri")
            if is_dir:
                dirs.append(file_uri)
            else:
                entry = SupernoteBrowserFile.from_json(file_obj)
                if entry.is_valid():
                    yield entry
                else:
                    logger.warning("Invalid file object: {}", file_obj)


def download_file(snf: SupernoteBrowserFile, config=snsync.config.global_config):
    target_path = config.sync_dir / snf.path.lstrip("/")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{config.supernote_url}/{snf.path.lstrip('/')}"
    try:
        logger.debug("Downloading {} to {}", url, target_path)
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        with target_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        raise FetchError(f"Error downloading {url}: {e}") from e


def upload_file(local_file: Union[str, Path], target_path: str, config=snsync.config.global_config):
    target_path: Path = Path(target_path.lstrip("/"))
    target_filename = target_path.name
    target_dir = target_path.parent.as_posix().lstrip()
    files = {"file": (target_filename, open(local_file, "rb"))}
    try:
        logger.debug("Uploading {} to {}", local_file, target_path)
        resp = requests.post(f"{config.supernote_url}/{target_dir}", files=files)
        resp.raise_for_status()
    except Exception as e:
        raise FetchError(f"Error uploading {local_file} to {target_path}: {e}") from e
