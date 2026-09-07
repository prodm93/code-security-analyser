"""Scanner orchestration behind one scanner-independent interface."""

from collections.abc import Sequence

from .adapter import ScannerAdapter
from .models import ScanResult, ScannerResult, ScanStatus, TargetType


class UnifiedScanner:
    """Dispatch targets to scanner adapters and aggregate normalized results."""

    def __init__(
        self,
        opengrep: ScannerAdapter,
        trivy: ScannerAdapter,
    ) -> None:
        self._opengrep = opengrep
        self._trivy = trivy

    def scan(self, target_type: TargetType | str, target: str) -> ScanResult:
        resolved_type = TargetType(target_type)
        resolved_target = target.strip()
        if not resolved_target:
            raise ValueError("Scan target cannot be empty")

        scanner_results = [
            self._run_adapter(adapter, resolved_target, resolved_type)
            for adapter in self._adapters_for(resolved_type)
        ]
        return ScanResult(
            target_type=resolved_type,
            target=resolved_target,
            status=_combined_status(scanner_results),
            scanner_results=scanner_results,
            total_findings=sum(len(result.findings) for result in scanner_results),
        )

    def _adapters_for(self, target_type: TargetType) -> Sequence[ScannerAdapter]:
        if target_type is TargetType.CODE:
            return (self._opengrep,)
        if target_type is TargetType.PROJECT:
            return (self._opengrep, self._trivy)
        return (self._trivy,)

    @staticmethod
    def _run_adapter(
        adapter: ScannerAdapter,
        target: str,
        target_type: TargetType,
    ) -> ScannerResult:
        try:
            return adapter.scan(target, target_type)
        except Exception as exc:
            return ScannerResult(
                scanner=adapter.name,
                status=ScanStatus.FAILED,
                error=f"Unexpected scanner failure: {str(exc)[:1_000]}",
            )


def _combined_status(results: list[ScannerResult]) -> ScanStatus:
    succeeded = sum(result.status is ScanStatus.SUCCEEDED for result in results)
    if succeeded == len(results):
        return ScanStatus.SUCCEEDED
    if succeeded:
        return ScanStatus.PARTIAL
    return ScanStatus.FAILED
