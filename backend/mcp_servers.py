"""
MCP server configurations and setup for security analysis tools.
"""

import os
import sys
from agents.mcp import MCPServerStdio


def create_scanner_server() -> MCPServerStdio:
    """Create the unified OpenGrep and Trivy MCP server."""
    server_path = os.path.join(os.path.dirname(__file__), "scanner_mcp_server.py")
    return MCPServerStdio(
        params={
            "command": sys.executable,
            "args": [server_path],
            "env": {**os.environ, "PYTHONUNBUFFERED": "1"},
        },
        client_session_timeout_seconds=240,
    )
