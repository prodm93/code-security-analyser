"""Small test adapters for scanner-module tests."""

from collections.abc import Sequence

from scanning.models import ScannerResult, TargetType
from scanning.process import ProcessResult


class StubRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[list[str], int]] = []

    def run(self, command: Sequence[str], timeout_seconds: int) -> ProcessResult:
        self.calls.append((list(command), timeout_seconds))
        return self.result


class StubAdapter:
    def __init__(self, name: str, result: ScannerResult) -> None:
        self.name = name
        self.result = result
        self.calls: list[tuple[str, TargetType]] = []

    def scan(self, target: str, target_type: TargetType) -> ScannerResult:
        self.calls.append((target, target_type))
        return self.result
