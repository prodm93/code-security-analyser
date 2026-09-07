import io
import os
import unittest
import zipfile
from contextlib import asynccontextmanager, nullcontext
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import server
from resource_limits import ProjectArchiveLimits

ANALYSIS_API_KEY = "test-analysis-key-that-is-at-least-32-chars"
AUTH_HEADERS = {"Authorization": f"Bearer {ANALYSIS_API_KEY}"}


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


class FullAnalysisCapacity:
    @asynccontextmanager
    async def reserve(self):
        raise server.AnalysisCapacityExceeded
        yield


class ServerRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(server.app)
        self.runner = AsyncMock(return_value=FakeAgentResult())
        self.patchers = [
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "ANALYSIS_API_KEY": ANALYSIS_API_KEY,
                },
            ),
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
        response = self.client.post(
            "/api/analyze",
            json={"code": "print('ok')"},
            headers=AUTH_HEADERS,
        )

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
            headers=AUTH_HEADERS,
        )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["summary"].startswith("Analyzed project"))
        agent = self.runner.await_args.args[0]
        self.assertEqual(1, len(agent.mcp_servers))

    def test_project_analysis_rejects_an_expansion_bomb(self) -> None:
        archive = io.BytesIO()
        with zipfile.ZipFile(
            archive, "w", compression=zipfile.ZIP_DEFLATED
        ) as zip_file:
            zip_file.writestr("large.py", b"x" * 100)
        constrained = server.ResourceLimits(
            code_request_bytes=server.resource_limits.code_request_bytes,
            image_request_bytes=server.resource_limits.image_request_bytes,
            project_archive=ProjectArchiveLimits(
                max_upload_bytes=1_024,
                max_extracted_bytes=10,
                max_members=10,
            ),
            max_concurrent_analyses=1,
            queue_timeout_seconds=1,
        )

        with patch.object(server, "resource_limits", constrained):
            response = self.client.post(
                "/api/analyze-project",
                files={"file": ("project.zip", archive.getvalue(), "application/zip")},
                headers=AUTH_HEADERS,
            )

        self.assertEqual(413, response.status_code)
        self.runner.assert_not_awaited()

    def test_image_analysis_route_uses_one_scanner_server(self) -> None:
        response = self.client.post(
            "/api/analyze-image",
            json={"image": "alpine:3.22"},
            headers=AUTH_HEADERS,
        )

        self.assertEqual(200, response.status_code)
        self.assertTrue(
            response.json()["summary"].startswith("Analyzed container image")
        )
        agent = self.runner.await_args.args[0]
        self.assertEqual(1, len(agent.mcp_servers))

    def test_analysis_routes_reject_work_when_capacity_is_full(self) -> None:
        with patch.object(server, "analysis_capacity", FullAnalysisCapacity()):
            response = self.client.post(
                "/api/analyze",
                json={"code": "print('ok')"},
                headers=AUTH_HEADERS,
            )

        self.assertEqual(429, response.status_code)
        self.assertEqual("1", response.headers["retry-after"])
        self.runner.assert_not_awaited()

    def test_analysis_routes_reject_missing_credentials(self) -> None:
        requests = (
            ("/api/analyze", {"json": {"code": "print('ok')"}}),
            ("/api/analyze-project", {"files": {"file": ("x.zip", b"bad")}}),
            ("/api/analyze-image", {"json": {"image": "alpine:3.22"}}),
        )

        for path, kwargs in requests:
            with self.subTest(path=path):
                response = self.client.post(path, **kwargs)
                self.assertEqual(401, response.status_code)
                self.assertEqual("Bearer", response.headers["www-authenticate"])

        self.runner.assert_not_awaited()

    def test_analysis_routes_fail_closed_when_auth_is_unconfigured(self) -> None:
        with patch.dict(os.environ, {"ANALYSIS_API_KEY": ""}):
            response = self.client.post(
                "/api/analyze",
                json={"code": "print('ok')"},
                headers=AUTH_HEADERS,
            )

        self.assertEqual(503, response.status_code)
        self.runner.assert_not_awaited()

    def test_analysis_routes_reject_an_incorrect_token(self) -> None:
        response = self.client.post(
            "/api/analyze",
            json={"code": "print('ok')"},
            headers={"Authorization": "Bearer definitely-not-the-right-token"},
        )

        self.assertEqual(401, response.status_code)
        self.runner.assert_not_awaited()

    def test_health_remains_available_without_credentials(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()
