import io
import os
import unittest
import zipfile
from contextlib import nullcontext
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import server


class FakeScannerContext:
    name = "test-scanners"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class FakeAgentResult:
    def final_output_as(self, output_type):
        return output_type(
            summary="Scanner analysis complete.",
            issues=[
                {
                    "title": "Lower priority",
                    "description": "Description",
                    "code": "example",
                    "fix": "Fix",
                    "cvss_score": 3.0,
                    "severity": "low",
                },
                {
                    "title": "Higher priority",
                    "description": "Description",
                    "code": "example",
                    "fix": "Fix",
                    "cvss_score": 9.0,
                    "severity": "critical",
                },
            ],
        )


class ServerRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(server.app)
        self.runner = AsyncMock(return_value=FakeAgentResult())
        self.patchers = [
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch("server.trace", return_value=nullcontext()),
            patch("server.create_scanner_server", side_effect=FakeScannerContext),
            patch.object(server.Runner, "run", self.runner),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()

    def test_code_analysis_route_uses_one_scanner_server(self) -> None:
        response = self.client.post("/api/analyze", json={"code": "print('ok')"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("Higher priority", payload["issues"][0]["title"])
        self.assertTrue(payload["summary"].startswith("Analyzed 11 characters"))
        agent = self.runner.await_args.args[0]
        self.assertEqual(1, len(agent.mcp_servers))

    def test_project_analysis_route_accepts_a_zip(self) -> None:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.writestr("app.py", "print('ok')")

        response = self.client.post(
            "/api/analyze-project",
            files={"file": ("project.zip", archive.getvalue(), "application/zip")},
        )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["summary"].startswith("Analyzed project"))
        agent = self.runner.await_args.args[0]
        self.assertEqual(1, len(agent.mcp_servers))

    def test_image_analysis_route_uses_one_scanner_server(self) -> None:
        response = self.client.post(
            "/api/analyze-image",
            json={"image": "alpine:3.22"},
        )

        self.assertEqual(200, response.status_code)
        self.assertTrue(
            response.json()["summary"].startswith("Analyzed container image")
        )
        agent = self.runner.await_args.args[0]
        self.assertEqual(1, len(agent.mcp_servers))


if __name__ == "__main__":
    unittest.main()
