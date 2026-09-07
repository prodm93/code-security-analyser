"""OpenGrep adapter and result normalization."""

import json
import subprocess

from .models import (
    Finding,
    FindingCategory,
    FindingLocation,
    ScannerResult,
    ScanStatus,
    TargetType,
)
from .normalization import (
    error_message,
    normalize_severity,
    string_list,
    unique_strings,
)
from .process import CommandRunner


class OpenGrepAdapter:
    name = "opengrep"

    def __init__(self, runner: CommandRunner, timeout_seconds: int = 120) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def scan(self, target: str, target_type: TargetType) -> ScannerResult:
        if target_type not in {TargetType.CODE, TargetType.PROJECT}:
            return self._failure(
                f"OpenGrep cannot scan target type '{target_type.value}'"
            )

        command = [
            "opengrep",
            "scan",
            "--config",
            "auto",
            "--json",
            "--quiet",
            target,
        ]
        try:
            completed = self._runner.run(command, self._timeout_seconds)
        except FileNotFoundError:
            return self._failure("OpenGrep executable was not found")
        except subprocess.TimeoutExpired:
            return self._failure(
                f"OpenGrep scan timed out after {self._timeout_seconds} seconds"
            )

        if completed.returncode != 0:
            return self._failure(
                error_message(
                    completed.stderr,
                    completed.stdout,
                    f"OpenGrep exited with status {completed.returncode}",
                )
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return self._failure("OpenGrep returned invalid JSON")

        if not isinstance(payload, dict):
            return self._failure("OpenGrep returned an unexpected JSON document")

        findings = [self._normalize(item) for item in payload.get("results", [])]
        warnings = [str(item)[:1_000] for item in payload.get("errors", [])]
        return ScannerResult(
            scanner=self.name,
            status=ScanStatus.SUCCEEDED,
            findings=findings,
            warnings=warnings,
        )

    def _normalize(self, raw: dict) -> Finding:
        extra = raw.get("extra") or {}
        metadata = extra.get("metadata") or {}
        rule_id = str(raw.get("check_id") or "unknown-rule")
        message = str(extra.get("message") or rule_id)

        return Finding(
            scanner=self.name,
            rule_id=rule_id,
            category=FindingCategory.SAST,
            severity=normalize_severity(extra.get("severity")),
            title=message,
            description=message,
            location=FindingLocation(
                path=_optional_string(raw.get("path")),
                start_line=_positive_int((raw.get("start") or {}).get("line")),
                end_line=_positive_int((raw.get("end") or {}).get("line")),
            ),
            evidence=str(extra.get("lines") or ""),
            remediation=str(metadata.get("fix") or metadata.get("impact") or ""),
            references=unique_strings(metadata.get("references")),
            metadata={
                "cwe": string_list(metadata.get("cwe")),
                "owasp": string_list(metadata.get("owasp")),
                "vulnerability_class": string_list(metadata.get("vulnerability_class")),
                "confidence": metadata.get("confidence"),
            },
        )

    def _failure(self, message: str) -> ScannerResult:
        return ScannerResult(
            scanner=self.name,
            status=ScanStatus.FAILED,
            error=message,
        )


def _optional_string(value: object) -> str | None:
    return str(value) if value not in {None, ""} else None


def _positive_int(value: object) -> int | None:
    return value if isinstance(value, int) and value > 0 else None
