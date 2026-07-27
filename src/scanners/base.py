from abc import ABC, abstractmethod
from src.models import Finding, ScanResult

class BaseScanner(ABC):

    @abstractmethod
    def scan(self, changed_files: list[str], config: dict) -> ScanResult:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_file_extensions(self) -> list[str]:
        pass