import unittest

from scanning.models import (
    Finding,
    FindingCategory,
    ScannerResult,
    ScanStatus,
    Severity,
    TargetType,
)
from scanning.scanner import UnifiedScanner
from tests.fakes import StubAdapter


def finding(scanner: str) -> Finding:
    return Finding(
        scanner=scanner,
        rule_id="rule-1",
        category=FindingCategory.SAST,
        severity=Severity.HIGH,
        title="Finding",
        description="Description",
    )


class UnifiedScannerTests(unittest.TestCase):
    def test_project_scan_runs_both_adapters_and_aggregates_results(self) -> None:
        opengrep = StubAdapter(
            "opengrep",
            ScannerResult(
                scanner="opengrep",
                status=ScanStatus.SUCCEEDED,
                findings=[finding("opengrep")],
            ),
        )
        trivy = StubAdapter(
            "trivy",
            ScannerResult(
                scanner="trivy",
                status=ScanStatus.SUCCEEDED,
                findings=[finding("trivy")],
            ),
        )

        result = UnifiedScanner(opengrep, trivy).scan("project", " /tmp/project ")

        self.assertEqual(ScanStatus.SUCCEEDED, result.status)
        self.assertEqual(2, result.total_findings)
        self.assertEqual([("/tmp/project", TargetType.PROJECT)], opengrep.calls)
        self.assertEqual([("/tmp/project", TargetType.PROJECT)], trivy.calls)

    def test_one_failed_project_scanner_produces_partial_status(self) -> None:
        opengrep = StubAdapter(
            "opengrep",
            ScannerResult(scanner="opengrep", status=ScanStatus.SUCCEEDED),
        )
        trivy = StubAdapter(
            "trivy",
            ScannerResult(
                scanner="trivy",
                status=ScanStatus.FAILED,
                error="scan failed",
            ),
        )

        result = UnifiedScanner(opengrep, trivy).scan("project", "/tmp/project")

        self.assertEqual(ScanStatus.PARTIAL, result.status)
        self.assertEqual("scan failed", result.scanner_results[1].error)

    def test_code_and_image_targets_use_only_the_applicable_adapter(self) -> None:
        opengrep = StubAdapter(
            "opengrep",
            ScannerResult(scanner="opengrep", status=ScanStatus.SUCCEEDED),
        )
        trivy = StubAdapter(
            "trivy",
            ScannerResult(scanner="trivy", status=ScanStatus.SUCCEEDED),
        )
        scanner = UnifiedScanner(opengrep, trivy)

        scanner.scan("code", "/tmp/example.py")
        scanner.scan("image", "alpine:3.22")

        self.assertEqual(1, len(opengrep.calls))
        self.assertEqual(1, len(trivy.calls))
        self.assertEqual(TargetType.CODE, opengrep.calls[0][1])
        self.assertEqual(TargetType.IMAGE, trivy.calls[0][1])


if __name__ == "__main__":
    unittest.main()
