"""
MCP server configurations and setup for security analysis tools.
"""

import os
import sys
from agents.mcp import MCPServerStdio

from scanning.environment import scanner_environment


def scanner_server_params() -> dict[str, object]:
    """Build stdio parameters without forwarding application credentials."""
    server_path = os.path.join(os.path.dirname(__file__), "scanner_mcp_server.py")
    environment = scanner_environment()
    environment["PYTHONUNBUFFERED"] = "1"
    return {
        "command": sys.executable,
        "args": [server_path],
        "env": environment,
    }


def create_scanner_server() -> MCPServerStdio:
    """Create the unified OpenGrep and Trivy MCP server."""
    return MCPServerStdio(
        params=scanner_server_params(),
        client_session_timeout_seconds=240,
    )
