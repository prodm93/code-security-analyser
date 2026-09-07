"""Subprocess seam shared by scanner adapters."""

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, Sequence

from scanning.environment import scanner_environment


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(self, command: Sequence[str], timeout_seconds: int) -> ProcessResult:
        """Run a command and capture its output."""


class SubprocessRunner:
    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = scanner_environment(environment)

    def run(self, command: Sequence[str], timeout_seconds: int) -> ProcessResult:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            env=self._environment,
            text=True,
            timeout=timeout_seconds,
        )
        return ProcessResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
