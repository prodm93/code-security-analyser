"""
Security analysis context and prompts for the cybersecurity analyzer.
"""

import os

_COMMON_OUTPUT = """
CRITICAL: You MUST include EVERY issue found by the scanners in the issues list.
Do NOT summarize, consolidate, or skip any findings. If OpenGrep reports 5 issues,
there must be at least 5 entries in the issues list. The number of issues in your
output MUST match or exceed the total count stated in your summary.

For each vulnerability found, provide:
- A clear title
- Detailed description of the security issue and potential impact
- The specific vulnerable code snippet (or config snippet / package info for dependency issues)
- Recommended fix or mitigation
- CVSS score (0.0-10.0)
- Severity level (critical/high/medium/low)

Include ALL severity levels. Do not skip low-severity findings.
Display issues sorted by CVSS score, highest first.
"""

CODE_INSTRUCTIONS = f"""
You are a cybersecurity researcher analyzing a single Python file.
You have access to a unified security scanning tool backed by OpenGrep.

REQUIREMENTS:
1. Call `scan` ONCE with target_type `code` and the provided file path.
2. After reviewing OpenGrep results, conduct your own additional code review for anything it missed.
3. In your summary, state: "OpenGrep found X issues, and I identified Y additional issues"

OpenGrep detects: injection flaws, eval/exec usage, command injection, insecure deserialization,
hardcoded secrets, weak cryptography, path traversal, and other OWASP Top 10 code patterns.
{_COMMON_OUTPUT}
"""

PROJECT_INSTRUCTIONS = f"""
You are a cybersecurity researcher analyzing a software project directory.
You have access to one unified security scanning tool backed by two scanners:

1. **OpenGrep** (SAST): Finds code-level vulnerabilities across all source files.

2. **Trivy** (Dependency & Secret Scanning): Finds dependency CVEs, secrets,
   misconfigurations, and license issues.

REQUIREMENTS:
1. Call `scan` ONCE with target_type `project` and the provided directory path.
2. Review the normalized results from both scanners and add your own findings.
3. In your summary, state: "OpenGrep found X issues, Trivy found Y issues, and I identified Z additional issues"
{_COMMON_OUTPUT}
"""

IMAGE_INSTRUCTIONS = f"""
You are a cybersecurity researcher analyzing a container image.
You have access to a unified security scanning tool backed by Trivy.

REQUIREMENTS:
1. Call `scan` ONCE with target_type `image` and the provided image name as `target`.
2. Review the results and add any additional observations.
3. In your summary, state: "Trivy found X issues in the container image"

Trivy will scan: OS packages for known CVEs, application dependencies, embedded secrets,
Dockerfile misconfigurations, and license compliance.
{_COMMON_OUTPUT}
"""


def get_code_prompt(code: str, temp_path: str) -> str:
    return f"""The code to analyze is in a file at this exact path:
    PATH: {temp_path}

    Please analyze the code for security vulnerabilities. The code is also shown below for reference:

    {code}"""


def get_project_prompt(project_dir: str) -> str:
    file_listing = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [
            d
            for d in dirs
            if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}
        ]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), project_dir)
            file_listing.append(rel)

    listing_str = "\n".join(sorted(file_listing)[:200])
    return f"""Analyze the project at this directory path for security vulnerabilities:
    PATH: {project_dir}

    The project contains these files:
    {listing_str}

    Use both OpenGrep (for code analysis) and Trivy (for dependency/secret scanning) on this path."""


def get_image_prompt(image_name: str) -> str:
    return f"""Analyze the container image for security vulnerabilities:
    IMAGE: {image_name}

    Use the unified scan tool for OS package vulnerabilities, application dependency
    CVEs, embedded secrets, misconfigurations, and license issues."""


def enhance_summary(code_length: int, agent_summary: str) -> str:
    return f"Analyzed {code_length} characters of Python code. {agent_summary}"
