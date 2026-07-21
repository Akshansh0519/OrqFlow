"""
mcp_servers/files_server.py — Sandboxed file operations MCP server (port 8003).

Tools exposed:
  - list_files(path)              → directory listing within the sandbox
  - read_file(path)               → file content as string
  - write_file(path, content)     → write/overwrite a file in the sandbox
  - lint_python(path)             → run ruff on a Python file, return diagnostics

Security model (Card 7 — File Ops Sandbox):
  - All paths are resolved relative to WORKSPACE_ROOT (/workspace in Docker)
  - Any path that resolves outside WORKSPACE_ROOT is rejected (path traversal prevention)
  - Code EXECUTION is deliberately excluded — only static analysis (ruff)
  - See Excluded Features section in orqflow_master_prompt.md for rationale

Interview answer for "how do you prevent path traversal?":
  "I resolve both the sandbox root and the requested path to their absolute
  canonical forms and check that the resolved path starts with the sandbox root.
  So '../../etc/passwd' resolves to '/etc/passwd', which doesn't start with
  '/workspace', so it's rejected before any filesystem operation."

Code execution is excluded. See orqflow_master_prompt.md §17 (Excluded Features).
"""

from __future__ import annotations

import json

# ── Sandbox root ──────────────────────────────────────────────────────────────
# Reads WORKSPACE_ROOT env var so any deployment platform can override it.
# Docker Compose: /workspace (named volume).  Render: /opt/render/project/src/workspace
# Tests: WORKSPACE_ROOT=./workspace pytest  (auto-created as needed).
import os as _os
import subprocess
from pathlib import Path

from fastmcp import FastMCP

from mcp_servers.shared_auth import verify_mcp_key

WORKSPACE_ROOT = Path(_os.environ.get("WORKSPACE_ROOT", "/workspace")).resolve()


def _safe_resolve(user_path: str) -> Path:
    """
    Resolve a user-supplied path to an absolute path within the sandbox.

    Steps:
      1. Reject absolute paths outright — both POSIX (/etc/passwd) and Windows (C:\\)
      2. Resolve to absolute canonical path relative to sandbox root
      3. Verify the resolved path is inside WORKSPACE_ROOT

    Raises:
        ValueError: If the path escapes the sandbox (path traversal attempt).
    """
    # Step 1: reject absolute paths before any resolution
    # On Windows, Path("/etc/passwd").is_absolute() is False (it's drive-relative),
    # so we also check for a leading slash explicitly for Unix-style absolute paths.
    p = Path(user_path)
    import re

    if (
        p.is_absolute()
        or user_path.startswith("/")
        or user_path.startswith("\\")
        or bool(re.match(r"^[a-zA-Z]:[/\\]", user_path))
    ):
        raise ValueError(
            f"Path traversal rejected: {user_path!r} is an absolute path. "
            "All paths must be relative to the sandbox root."
        )

    # Step 2: resolve relative to sandbox
    candidate = (WORKSPACE_ROOT / user_path).resolve()

    # Step 3: verify it's still inside the sandbox
    try:
        candidate.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise ValueError(
            f"Path traversal rejected: {user_path!r} resolves outside the sandbox. "
            f"All paths must stay within {WORKSPACE_ROOT}."
        )

    return candidate


# ── FastMCP server instance ───────────────────────────────────────────────────
mcp = FastMCP(
    name="orqflow-files",
    instructions=(
        "Sandboxed file operations within the /workspace directory. "
        "Paths are always relative to the sandbox root. "
        "Path traversal (e.g. '../etc/passwd') is rejected. "
        "Code execution is not supported — use lint_python for static analysis only."
    ),
)


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
async def list_files(path: str = "") -> list[str]:
    """
    List files and directories within the sandbox.

    Args:
        path: Relative path within the sandbox to list. Empty string = root.

    Returns:
        A list of relative path strings (files and directories).
    """
    verify_mcp_key()
    target = _safe_resolve(path)

    if not target.exists():
        return []  # Empty listing for non-existent directory

    if target.is_file():
        return [str(target.relative_to(WORKSPACE_ROOT))]

    return [str(p.relative_to(WORKSPACE_ROOT)) for p in sorted(target.iterdir())]


@mcp.tool()
async def read_file(path: str) -> str:
    """
    Read the content of a file within the sandbox.

    Args:
        path: Relative path to the file within the sandbox.

    Returns:
        The file content as a string (UTF-8).

    Raises:
        ValueError: If the path is outside the sandbox.
        FileNotFoundError: If the file does not exist.
    """
    verify_mcp_key()
    target = _safe_resolve(path)

    if not target.exists():
        raise FileNotFoundError(f"File not found: {path!r}")

    if not target.is_file():
        raise ValueError(f"Path is a directory, not a file: {path!r}")

    return target.read_text(encoding="utf-8")


@mcp.tool()
async def write_file(path: str, content: str) -> dict:
    """
    Write content to a file within the sandbox, creating parent directories as needed.

    Args:
        path: Relative path to the file within the sandbox.
        content: The string content to write (UTF-8).

    Returns:
        {"written": true, "path": "<relative path>", "bytes": <byte count>}

    Raises:
        ValueError: If the path is outside the sandbox.
    """
    verify_mcp_key()
    target = _safe_resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return {
        "written": True,
        "path": str(target.relative_to(WORKSPACE_ROOT)),
        "bytes": len(content.encode("utf-8")),
    }


@mcp.tool()
async def lint_python(path: str) -> dict:
    """
    Run ruff static analysis on a Python file within the sandbox.

    Args:
        path: Relative path to a .py file within the sandbox.

    Returns:
        {"clean": bool, "issues": list[str], "summary": str}
        issues: List of ruff diagnostic strings (empty if clean).

    Raises:
        ValueError: If the path is outside the sandbox or not a .py file.
        FileNotFoundError: If the file does not exist.

    NOTE: This is STATIC ANALYSIS only. Code is never executed.
    See Excluded Features in the master prompt for why code execution is excluded.
    """
    verify_mcp_key()
    target = _safe_resolve(path)

    if not target.exists():
        raise FileNotFoundError(f"File not found: {path!r}")

    if target.suffix != ".py":
        raise ValueError(f"lint_python only accepts .py files. Got: {path!r}")

    result = subprocess.run(
        ["ruff", "check", "--output-format=json", str(target)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    try:
        diagnostics = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        diagnostics = []

    issues = [
        f"{d.get('filename', '?')}:{d.get('location', {}).get('row', '?')}: "
        f"[{d.get('code', '?')}] {d.get('message', '?')}"
        for d in diagnostics
    ]

    return {
        "clean": len(issues) == 0,
        "issues": issues,
        "summary": f"{len(issues)} issue(s) found" if issues else "No issues found",
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=8003)
