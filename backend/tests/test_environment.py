import os
import subprocess
import unittest
from unittest.mock import patch

from mcp_servers import scanner_server_params
from scanning.environment import scanner_environment
from scanning.process import SubprocessRunner


class ScannerEnvironmentTests(unittest.TestCase):
    def test_allowlist_keeps_runtime_configuration_and_removes_credentials(
        self,
    ) -> None:
        source = {
            "PATH": "/usr/local/bin:/usr/bin",
            "HOME": "/tmp/scanner-home",
            "TRIVY_CACHE_DIR": "/tmp/trivy",
            "OPENAI_API_KEY": "openai-secret",
            "ANALYSIS_API_KEY": "analysis-secret",
            "SEMGREP_APP_TOKEN": "unused-secret",
            "UNRELATED_SECRET": "other-secret",
        }

        environment = scanner_environment(source)

        self.assertEqual(
            {
                "PATH": "/usr/local/bin:/usr/bin",
                "HOME": "/tmp/scanner-home",
                "TRIVY_CACHE_DIR": "/tmp/trivy",
            },
            environment,
        )

    def test_mcp_server_receives_only_the_scanner_environment(self) -> None:
        source = {
            "PATH": "/usr/bin",
            "OPENAI_API_KEY": "openai-secret",
            "ANALYSIS_API_KEY": "analysis-secret",
        }
        with patch.dict(os.environ, source, clear=True):
            params = scanner_server_params()

        self.assertEqual(
            {"PATH": "/usr/bin", "PYTHONUNBUFFERED": "1"},
            params["env"],
        )

    @patch("scanning.process.subprocess.run")
    def test_subprocess_runner_uses_an_explicit_sanitized_environment(
        self,
        run: unittest.mock.Mock,
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "output", "")
        runner = SubprocessRunner(
            {
                "PATH": "/usr/bin",
                "OPENAI_API_KEY": "openai-secret",
                "ANALYSIS_API_KEY": "analysis-secret",
            }
        )

        runner.run(["scanner", "target"], timeout_seconds=30)

        self.assertEqual({"PATH": "/usr/bin"}, run.call_args.kwargs["env"])


if __name__ == "__main__":
    unittest.main()
