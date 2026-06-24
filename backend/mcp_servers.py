"""
MCP server configurations and setup for security analysis tools.
"""

import os
import sys
import shutil
from typing import Dict, Any
from agents.mcp import MCPServerStdio


def get_trivy_server_params() -> Dict[str, Any]:
    """Get configuration parameters for the Trivy MCP server."""
    trivy_path = shutil.which("trivy")
    if not trivy_path:
        raise RuntimeError(
            "Trivy is not installed. "
            "Install with: brew install trivy (Mac) or see https://trivy.dev"
        )

    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
    }

    return {"command": "trivy", "args": ["mcp"], "env": env}


def create_trivy_server() -> MCPServerStdio:
    """Create and configure the Trivy MCP server instance."""
    params = get_trivy_server_params()
    return MCPServerStdio(
        params=params,
        client_session_timeout_seconds=240,
    )


def create_opengrep_server() -> MCPServerStdio:
    """Create and configure the OpenGrep MCP server instance."""
    server_path = os.path.join(os.path.dirname(__file__), "opengrep_mcp_server.py")
    return MCPServerStdio(
        params={
            "command": sys.executable,
            "args": [server_path],
            "env": {**os.environ, "PYTHONUNBUFFERED": "1"},
        },
        client_session_timeout_seconds=120,
    )
