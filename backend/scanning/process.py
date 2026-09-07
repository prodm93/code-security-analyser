"""Subprocess seam shared by scanner adapters."""

import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(self, command: Sequence[str], timeout_seconds: int) -> ProcessResult:
        """Run a command and capture its output."""


class SubprocessRunner:
    def run(self, command: Sequence[str], timeout_seconds: int) -> ProcessResult:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return ProcessResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
