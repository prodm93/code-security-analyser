import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cors_policy import CorsPolicy, install_cors


class CorsPolicyTests(unittest.TestCase):
    def test_production_defaults_to_same_origin_only(self) -> None:
        policy = CorsPolicy.from_environment({"ENVIRONMENT": "production"})

        self.assertEqual((), policy.allowed_origins)

    def test_development_keeps_local_frontend_origins(self) -> None:
        policy = CorsPolicy.from_environment({})

        self.assertIn("http://localhost:3000", policy.allowed_origins)
        self.assertNotIn("*", policy.allowed_origins)

    def test_explicit_origins_are_normalized_and_deduplicated(self) -> None:
        policy = CorsPolicy.from_environment(
            {
                "ENVIRONMENT": "production",
                "CORS_ALLOWED_ORIGINS": (
                    "https://ui.example.test/, https://admin.example.test, "
                    "https://ui.example.test"
                ),
            }
        )

        self.assertEqual(
            (
                "https://ui.example.test",
                "https://admin.example.test",
            ),
            policy.allowed_origins,
        )

    def test_wildcard_origins_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not contain a wildcard"):
            CorsPolicy.from_environment({"CORS_ALLOWED_ORIGINS": "*"})

    def test_installed_policy_allows_only_configured_frontends(self) -> None:
        cors_app = FastAPI()

        @cors_app.post("/api/analyze")
        async def analyze() -> dict[str, bool]:
            return {"ok": True}

        install_cors(
            cors_app,
            CorsPolicy(allowed_origins=("https://ui.example.test",)),
        )
        client = TestClient(cors_app)
        preflight_headers = {
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        }

        allowed = client.options(
            "/api/analyze",
            headers={"Origin": "https://ui.example.test", **preflight_headers},
        )
        denied = client.options(
            "/api/analyze",
            headers={"Origin": "https://attacker.example", **preflight_headers},
        )

        self.assertEqual(200, allowed.status_code)
        self.assertEqual(
            "https://ui.example.test",
            allowed.headers["access-control-allow-origin"],
        )
        self.assertNotIn("access-control-allow-credentials", allowed.headers)
        self.assertEqual(400, denied.status_code)
        self.assertNotIn("access-control-allow-origin", denied.headers)


if __name__ == "__main__":
    unittest.main()
