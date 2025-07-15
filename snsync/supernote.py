import json
import re
from pathlib import Path
from typing import Iterator, Optional, Union

import requests
from loguru import logger

from snsync.schema import SupernoteFileMeta

RE_JSON = re.compile(r"const json = '({[^']+})'")


class SupernoteClientError(Exception):
    pass


class SupernoteClient:
    def __init__(self, supernote_url: str, device_name: Optional[str] = None):
        self.base_url = supernote_url
        self.device_name = device_name

    def _get_page_json_data(self, path="/") -> dict:
        url = f"{self.base_url}{path}"
        try:
            logger.info("Fetching {}", url)
            contents = requests.get(url).text
        except requests.exceptions.RequestException as e:
            raise SupernoteClientError(f"Error fetching {url}: {e}") from e

        json_str = RE_JSON.search(contents).group(1)
        if not json_str:
            s
        return json.loads(json_str)

    def ping(self, timeout=1) -> bool:
        try:
            requests.options(self.base_url, timeout=timeout)
            return True
        except Exception:
            return False

    def list_files(self, path="/", recursive=True, include_dirs=False) -> Iterator[SupernoteFileMeta]:
        dirs = [path]
        while dirs:
            path = dirs.pop(0)
            data = self._get_page_json_data(path)
            device_name = data.get("deviceName")
            if self.device_name and device_name != self.device_name:
                raise SupernoteClientError(f"Device name mismatch: {device_name} != {self.device_name}")

            file_list = data.get("fileList", [])
            for file_obj in file_list:
                logger.debug("Got file {}", file_obj)
                is_dir = file_obj.get("isDirectory", False)
                file_uri = file_obj.get("uri")
                if is_dir and recursive:
                    dirs.append(file_uri)
                if not is_dir or include_dirs:
                    sn_meta = SupernoteFileMeta.from_json_data(device_name, file_obj)
                    if sn_meta.is_valid():
                        yield sn_meta
                    else:
                        logger.warning("Invalid file object: {}", file_obj)

    def download(self, src: Union[str, SupernoteFileMeta], target: Union[str, Path]):
        if isinstance(src, SupernoteFileMeta):
            src_path = src.path
        else:
            src_path = src
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        src_url = f"{self.base_url}/{src_path.lstrip('/')}"
        try:
            logger.info("Downloading {} to {}", src_url, target_path)
            resp = requests.get(src_url, stream=True)
            resp.raise_for_status()
            with target_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            raise SupernoteClientError(f"Error downloading {src_url}: {e}") from e

    def upload(self, src: Union[str, Path], target: Union[str, SupernoteFileMeta]):
        if isinstance(target, SupernoteFileMeta):
            target_path = Path(target.path.lstrip("/"))
        else:
            target_path = Path(target.lstrip("/"))

        target_filename = target_path.name
        target_dir = target_path.parent.as_posix()
        files = {"file": (target_filename, open(src, "rb"))}
        try:
            logger.info("Uploading {} to {}", src, target_path)
            resp = requests.post(f"{self.base_url}/{target_dir}", files=files)
            resp.raise_for_status()
        except Exception as e:
            raise SupernoteClientError(f"Error uploading {src} to {target_path}: {e}") from e
