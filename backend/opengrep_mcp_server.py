"""
Lightweight MCP server that wraps the OpenGrep CLI for SAST scanning.
"""

import json
import subprocess
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("opengrep")


@mcp.tool()
def opengrep_scan(target: str, config: str = "auto") -> str:
    """Scan a file or directory for security vulnerabilities using OpenGrep static analysis.

    Args:
        target: Absolute path to the file or directory to scan.
        config: Rule configuration - use "auto" for automatic rules from the registry,
                or a path to a custom YAML rules file. Default is "auto".

    Returns:
        JSON string containing scan results with identified vulnerabilities,
        including rule IDs, severity, CWE references, and remediation guidance.
    """
    cmd = ["opengrep", "scan", "--config", config, "--json", "--quiet", target]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return json.dumps({"error": "OpenGrep is not installed. Install from https://github.com/opengrep/opengrep"})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "OpenGrep scan timed out after 120 seconds"})

    stdout = result.stdout.strip()
    if not stdout:
        return json.dumps({"results": [], "message": "No output from OpenGrep"})

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return json.dumps({"error": "Failed to parse OpenGrep output", "raw": stdout[:2000]})

    results = data.get("results", [])
    findings = []
    for r in results:
        extra = r.get("extra", {})
        metadata = extra.get("metadata", {})
        findings.append({
            "rule_id": r.get("check_id", ""),
            "path": r.get("path", ""),
            "start_line": r.get("start", {}).get("line"),
            "end_line": r.get("end", {}).get("line"),
            "message": extra.get("message", ""),
            "severity": extra.get("severity", ""),
            "code_snippet": extra.get("lines", ""),
            "cwe": metadata.get("cwe", []),
            "owasp": metadata.get("owasp", []),
            "vulnerability_class": metadata.get("vulnerability_class", []),
            "confidence": metadata.get("confidence", ""),
            "impact": metadata.get("impact", ""),
            "references": metadata.get("references", []),
        })

    return json.dumps({
        "total_findings": len(findings),
        "findings": findings,
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
