"""Internal scanner-adapter seam."""

from typing import Protocol

from .models import ScannerResult, TargetType


class ScannerAdapter(Protocol):
    name: str

    def scan(self, target: str, target_type: TargetType) -> ScannerResult:
        """Scan one target and return scanner-independent findings."""
