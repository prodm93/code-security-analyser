import json
import unittest

from scanning.models import FindingCategory, ScanStatus, Severity, TargetType
from scanning.opengrep import OpenGrepAdapter
from scanning.process import ProcessResult
from tests.fakes import StubRunner


class OpenGrepAdapterTests(unittest.TestCase):
    def test_normalizes_findings_into_the_common_schema(self) -> None:
        payload = {
            "results": [
                {
                    "check_id": "python.lang.security.audit.eval-detected",
                    "path": "/tmp/example.py",
                    "start": {"line": 4},
                    "end": {"line": 4},
                    "extra": {
                        "message": "Use of eval detected",
                        "severity": "ERROR",
                        "lines": "eval(user_input)",
                        "metadata": {
                            "cwe": ["CWE-95"],
                            "owasp": "A03:2021",
                            "confidence": "HIGH",
                            "references": ["https://example.test/rule"],
                        },
                    },
                }
            ]
        }
        runner = StubRunner(ProcessResult(0, json.dumps(payload), ""))

        result = OpenGrepAdapter(runner).scan("/tmp/example.py", TargetType.CODE)

        self.assertEqual(ScanStatus.SUCCEEDED, result.status)
        self.assertEqual(1, len(result.findings))
        finding = result.findings[0]
        self.assertEqual("opengrep", finding.scanner)
        self.assertEqual(FindingCategory.SAST, finding.category)
        self.assertEqual(Severity.HIGH, finding.severity)
        self.assertEqual(4, finding.location.start_line)
        self.assertEqual(["CWE-95"], finding.metadata["cwe"])
        command, timeout = runner.calls[0]
        self.assertEqual("opengrep", command[0])
        self.assertEqual("/tmp/example.py", command[-1])
        self.assertEqual(120, timeout)

    def test_reports_nonzero_exit_as_a_scanner_failure(self) -> None:
        runner = StubRunner(ProcessResult(2, "", "configuration failed"))

        result = OpenGrepAdapter(runner).scan("/tmp/example.py", TargetType.CODE)

        self.assertEqual(ScanStatus.FAILED, result.status)
        self.assertEqual("configuration failed", result.error)
        self.assertEqual([], result.findings)


if __name__ == "__main__":
    unittest.main()
