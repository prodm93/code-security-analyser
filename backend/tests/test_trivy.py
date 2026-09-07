import json
import unittest

from scanning.models import FindingCategory, ScanStatus, Severity, TargetType
from scanning.process import ProcessResult
from scanning.trivy import TrivyAdapter
from tests.fakes import StubRunner


class TrivyAdapterTests(unittest.TestCase):
    def test_normalizes_every_supported_finding_type(self) -> None:
        payload = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "requirements.txt",
                    "Class": "lang-pkgs",
                    "Type": "pip",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2026-0001",
                            "PkgID": "demo@1.0",
                            "PkgName": "demo",
                            "InstalledVersion": "1.0",
                            "FixedVersion": "1.1",
                            "Severity": "CRITICAL",
                            "Title": "Demo vulnerability",
                            "Description": "A vulnerable package",
                            "PrimaryURL": "https://example.test/cve",
                            "CweIDs": ["CWE-79"],
                        }
                    ],
                    "Misconfigurations": [
                        {
                            "ID": "DS-0002",
                            "Title": "Container runs as root",
                            "Description": "No USER instruction",
                            "Message": "Specify a non-root user",
                            "Resolution": "Add USER",
                            "Severity": "HIGH",
                            "Status": "FAIL",
                            "CauseMetadata": {"StartLine": 1, "EndLine": 2},
                        }
                    ],
                    "Secrets": [
                        {
                            "RuleID": "generic-api-key",
                            "Category": "General",
                            "Severity": "HIGH",
                            "Title": "API key",
                            "StartLine": 8,
                            "EndLine": 8,
                            "Match": "do-not-leak-this-value",
                        }
                    ],
                    "Licenses": [
                        {
                            "Severity": "LOW",
                            "Category": "notice",
                            "PkgName": "demo",
                            "FilePath": "LICENSE",
                            "Name": "BSD-3-Clause",
                            "Confidence": 1,
                            "Link": "https://spdx.org/licenses/BSD-3-Clause.html",
                        }
                    ],
                }
            ],
        }
        runner = StubRunner(ProcessResult(0, json.dumps(payload), ""))

        result = TrivyAdapter(runner).scan("/tmp/project", TargetType.PROJECT)

        self.assertEqual(ScanStatus.SUCCEEDED, result.status)
        self.assertEqual(
            [
                FindingCategory.VULNERABILITY,
                FindingCategory.MISCONFIGURATION,
                FindingCategory.SECRET,
                FindingCategory.LICENSE,
            ],
            [finding.category for finding in result.findings],
        )
        self.assertEqual(Severity.CRITICAL, result.findings[0].severity)
        self.assertEqual("demo", result.findings[0].location.package_name)
        self.assertNotIn("do-not-leak-this-value", result.model_dump_json())
        command, timeout = runner.calls[0]
        self.assertEqual("filesystem", command[1])
        self.assertEqual("/tmp/project", command[-1])
        self.assertEqual(240, timeout)

    def test_accepts_omitted_result_and_finding_collections(self) -> None:
        runner = StubRunner(ProcessResult(0, json.dumps({"SchemaVersion": 2}), ""))

        result = TrivyAdapter(runner).scan("alpine:3.22", TargetType.IMAGE)

        self.assertEqual(ScanStatus.SUCCEEDED, result.status)
        self.assertEqual([], result.findings)
        self.assertEqual("image", runner.calls[0][0][1])

    def test_rejects_an_unknown_json_schema(self) -> None:
        runner = StubRunner(ProcessResult(0, json.dumps({"SchemaVersion": 3}), ""))

        result = TrivyAdapter(runner).scan("alpine:3.22", TargetType.IMAGE)

        self.assertEqual(ScanStatus.FAILED, result.status)
        self.assertIn("schema version", result.error or "")


if __name__ == "__main__":
    unittest.main()
