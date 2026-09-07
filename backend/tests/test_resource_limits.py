import asyncio
import unittest

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from resource_limits import (
    AnalysisCapacity,
    AnalysisCapacityExceeded,
    RequestBodyLimitMiddleware,
    ResourceLimits,
)


class ResourceLimitConfigurationTests(unittest.TestCase):
    def test_loads_overrides_from_the_environment(self) -> None:
        configured = ResourceLimits.from_environment(
            {
                "MAX_CODE_REQUEST_BYTES": "100",
                "MAX_IMAGE_REQUEST_BYTES": "101",
                "MAX_PROJECT_UPLOAD_BYTES": "102",
                "MAX_PROJECT_EXTRACTED_BYTES": "103",
                "MAX_PROJECT_FILES": "104",
                "MAX_CONCURRENT_ANALYSES": "2",
                "ANALYSIS_QUEUE_TIMEOUT_SECONDS": "0.5",
            }
        )

        self.assertEqual(100, configured.code_request_bytes)
        self.assertEqual(103, configured.project_archive.max_extracted_bytes)
        self.assertEqual(104, configured.project_archive.max_members)
        self.assertEqual(2, configured.max_concurrent_analyses)
        self.assertEqual(0.5, configured.queue_timeout_seconds)

    def test_rejects_oversized_request_bodies(self) -> None:
        limited_app = FastAPI()
        limited_app.add_middleware(
            RequestBodyLimitMiddleware,
            path_limits={"/upload": 8},
        )

        @limited_app.post("/upload")
        async def upload(request: Request) -> dict[str, int]:
            return {"size": len(await request.body())}

        client = TestClient(limited_app)
        responses = (
            client.post("/upload", content=b"123456789"),
            client.post(
                "/upload",
                content=b"123456789",
                headers={"Content-Length": "1"},
            ),
        )

        for response in responses:
            with self.subTest(response=response):
                self.assertEqual(413, response.status_code)


class AnalysisCapacityTests(unittest.IsolatedAsyncioTestCase):
    async def test_times_out_instead_of_queueing_unbounded_work(self) -> None:
        capacity = AnalysisCapacity(maximum=1, queue_timeout_seconds=0.01)

        async with capacity.reserve():
            with self.assertRaises(AnalysisCapacityExceeded):
                async with capacity.reserve():
                    self.fail("A second analysis should not acquire the only slot")

        async with capacity.reserve():
            await asyncio.sleep(0)


if __name__ == "__main__":
    unittest.main()
