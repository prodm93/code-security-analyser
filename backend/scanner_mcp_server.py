"""MCP transport for the unified security-scanner module."""

from typing import Literal

from mcp.server.fastmcp import FastMCP

from scanning.opengrep import OpenGrepAdapter
from scanning.process import SubprocessRunner
from scanning.scanner import UnifiedScanner
from scanning.trivy import TrivyAdapter

mcp = FastMCP("security-scanners")


def create_scanner() -> UnifiedScanner:
    runner = SubprocessRunner()
    return UnifiedScanner(
        opengrep=OpenGrepAdapter(runner),
        trivy=TrivyAdapter(runner),
    )


@mcp.tool()
def scan(
    target_type: Literal["code", "project", "image"],
    target: str,
) -> dict:
    """Scan a target and return findings normalized across all applicable scanners.

    Use ``code`` for one source file, ``project`` for a source directory, and
    ``image`` for a container image reference. Project scans run both OpenGrep
    and Trivy; code and image scans run the applicable scanner.
    """
    result = create_scanner().scan(target_type, target)
    return result.model_dump(mode="json", exclude_none=True)


if __name__ == "__main__":
    mcp.run(transport="stdio")
