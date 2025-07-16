from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable


class Converter(ABC):
    @classmethod
    @abstractmethod
    def input_extensions(cls) -> Iterable[str]:
        pass

    @classmethod
    @abstractmethod
    def output_extension(cls) -> str:
        pass

    @abstractmethod
    def convert(self, input_path: str | Path, output_dir: str | Path) -> Path:
        pass
