"""Trivy adapter and result normalization."""

import json
import subprocess
from collections.abc import Callable
from typing import Any

from .models import (
    Finding,
    FindingCategory,
    FindingLocation,
    ScannerResult,
    ScanStatus,
    TargetType,
)
from .normalization import error_message, normalize_severity, unique_strings
from .process import CommandRunner


class TrivyAdapter:
    name = "trivy"
    schema_version = 2

    def __init__(self, runner: CommandRunner, timeout_seconds: int = 240) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def scan(self, target: str, target_type: TargetType) -> ScannerResult:
        subcommand = self._subcommand(target_type)
        if subcommand is None:
            return self._failure(f"Trivy cannot scan target type '{target_type.value}'")

        command = [
            "trivy",
            subcommand,
            "--scanners",
            "vuln,misconfig,secret,license",
            "--severity",
            "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
            "--format",
            "json",
            "--quiet",
            target,
        ]
        try:
            completed = self._runner.run(command, self._timeout_seconds)
        except FileNotFoundError:
            return self._failure("Trivy executable was not found")
        except subprocess.TimeoutExpired:
            return self._failure(
                f"Trivy scan timed out after {self._timeout_seconds} seconds"
            )

        if completed.returncode != 0:
            return self._failure(
                error_message(
                    completed.stderr,
                    completed.stdout,
                    f"Trivy exited with status {completed.returncode}",
                )
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return self._failure("Trivy returned invalid JSON")

        if not isinstance(payload, dict):
            return self._failure("Trivy returned an unexpected JSON document")
        if payload.get("SchemaVersion") != self.schema_version:
            return self._failure(
                "Unsupported Trivy JSON schema version: "
                f"{payload.get('SchemaVersion')!r}"
            )

        findings: list[Finding] = []
        for result in payload.get("Results") or []:
            findings.extend(self._normalize_result(result))

        return ScannerResult(
            scanner=self.name,
            status=ScanStatus.SUCCEEDED,
            findings=findings,
        )

    @staticmethod
    def _subcommand(target_type: TargetType) -> str | None:
        if target_type is TargetType.PROJECT:
            return "filesystem"
        if target_type is TargetType.IMAGE:
            return "image"
        return None

    def _normalize_result(self, result: dict[str, Any]) -> list[Finding]:
        normalizers: tuple[tuple[str, Callable[[dict, dict], Finding]], ...] = (
            ("Vulnerabilities", self._vulnerability),
            ("Misconfigurations", self._misconfiguration),
            ("Secrets", self._secret),
            ("Licenses", self._license),
        )
        findings: list[Finding] = []
        for field, normalize in normalizers:
            for raw in result.get(field) or []:
                findings.append(normalize(raw, result))
        return findings

    def _vulnerability(self, raw: dict, result: dict) -> Finding:
        rule_id = str(raw.get("VulnerabilityID") or "unknown-vulnerability")
        package = _optional_string(raw.get("PkgName"))
        installed = _optional_string(raw.get("InstalledVersion"))
        fixed = _optional_string(raw.get("FixedVersion"))
        remediation = ""
        if package and fixed:
            remediation = f"Upgrade {package} to {fixed} or later."

        return Finding(
            scanner=self.name,
            rule_id=rule_id,
            category=FindingCategory.VULNERABILITY,
            severity=normalize_severity(raw.get("Severity")),
            title=str(raw.get("Title") or rule_id),
            description=str(raw.get("Description") or raw.get("Title") or rule_id),
            location=FindingLocation(
                path=_optional_string(result.get("Target")),
                package_name=package,
                installed_version=installed,
                fixed_version=fixed,
            ),
            evidence=_package_evidence(package, installed),
            remediation=remediation,
            references=unique_strings(raw.get("PrimaryURL"), raw.get("References")),
            metadata={
                "class": result.get("Class"),
                "type": result.get("Type"),
                "package_id": raw.get("PkgID"),
                "status": raw.get("Status"),
                "cwe": raw.get("CweIDs") or [],
                "cvss": raw.get("CVSS") or {},
            },
        )

    def _misconfiguration(self, raw: dict, result: dict) -> Finding:
        rule_id = str(raw.get("ID") or "unknown-misconfiguration")
        cause = raw.get("CauseMetadata") or {}
        return Finding(
            scanner=self.name,
            rule_id=rule_id,
            category=FindingCategory.MISCONFIGURATION,
            severity=normalize_severity(raw.get("Severity")),
            title=str(raw.get("Title") or rule_id),
            description=str(raw.get("Description") or raw.get("Message") or rule_id),
            location=FindingLocation(
                path=_optional_string(result.get("Target")),
                start_line=_positive_int(cause.get("StartLine")),
                end_line=_positive_int(cause.get("EndLine")),
            ),
            evidence=str(raw.get("Message") or ""),
            remediation=str(raw.get("Resolution") or ""),
            references=unique_strings(raw.get("PrimaryURL"), raw.get("References")),
            metadata={
                "type": raw.get("Type"),
                "namespace": raw.get("Namespace"),
                "status": raw.get("Status"),
            },
        )

    def _secret(self, raw: dict, result: dict) -> Finding:
        rule_id = str(raw.get("RuleID") or "unknown-secret")
        return Finding(
            scanner=self.name,
            rule_id=rule_id,
            category=FindingCategory.SECRET,
            severity=normalize_severity(raw.get("Severity")),
            title=str(raw.get("Title") or rule_id),
            description=str(raw.get("Title") or "Potential secret detected"),
            location=FindingLocation(
                path=_optional_string(result.get("Target")),
                start_line=_positive_int(raw.get("StartLine")),
                end_line=_positive_int(raw.get("EndLine")),
            ),
            evidence="Secret value redacted by the normalization layer.",
            remediation="Remove the secret, rotate it, and load it from a secret manager.",
            metadata={"secret_category": raw.get("Category")},
        )

    def _license(self, raw: dict, result: dict) -> Finding:
        name = str(raw.get("Name") or "unknown-license")
        category = str(raw.get("Category") or "unknown")
        package = _optional_string(raw.get("PkgName"))
        return Finding(
            scanner=self.name,
            rule_id=name,
            category=FindingCategory.LICENSE,
            severity=normalize_severity(raw.get("Severity")),
            title=f"{name} license detected",
            description=f"Trivy classified this license as '{category}'.",
            location=FindingLocation(
                path=_optional_string(raw.get("FilePath") or result.get("Target")),
                package_name=package,
            ),
            evidence=f"Detected license: {name}",
            remediation="Review the license obligations against the project's policy.",
            references=unique_strings(raw.get("Link")),
            metadata={
                "license_category": category,
                "confidence": raw.get("Confidence"),
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


def _package_evidence(package: str | None, installed: str | None) -> str:
    if package and installed:
        return f"{package} {installed}"
    return package or installed or ""
