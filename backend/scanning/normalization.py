"""Small normalization helpers shared by scanner adapters."""

from typing import Any

from .models import Severity


_SEVERITY_ALIASES = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "ERROR": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "WARNING": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "INFO": Severity.INFO,
}


def normalize_severity(value: Any) -> Severity:
    return _SEVERITY_ALIASES.get(str(value or "").upper(), Severity.UNKNOWN)


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


def unique_strings(*values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in string_list(value):
            if item not in result:
                result.append(item)
    return result


def error_message(stderr: str, stdout: str, fallback: str) -> str:
    message = stderr.strip() or stdout.strip() or fallback
    return message[:2_000]
