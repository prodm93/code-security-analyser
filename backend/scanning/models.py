"""Scanner-independent request and result models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TargetType(str, Enum):
    CODE = "code"
    PROJECT = "project"
    IMAGE = "image"


class ScanStatus(str, Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


class FindingCategory(str, Enum):
    SAST = "sast"
    VULNERABILITY = "vulnerability"
    MISCONFIGURATION = "misconfiguration"
    SECRET = "secret"
    LICENSE = "license"


class FindingLocation(BaseModel):
    path: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    package_name: str | None = None
    installed_version: str | None = None
    fixed_version: str | None = None


class Finding(BaseModel):
    scanner: str
    rule_id: str
    category: FindingCategory
    severity: Severity
    title: str
    description: str
    location: FindingLocation = Field(default_factory=FindingLocation)
    evidence: str = ""
    remediation: str = ""
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScannerResult(BaseModel):
    scanner: str
    status: ScanStatus
    findings: list[Finding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class ScanResult(BaseModel):
    target_type: TargetType
    target: str
    status: ScanStatus
    scanner_results: list[ScannerResult]
    total_findings: int = Field(ge=0)
