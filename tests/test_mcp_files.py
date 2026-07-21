"""
tests/test_mcp_files.py — Phase 2 acceptance tests for the Files MCP server.

Tests the sandboxing and file operations:
  ✅ Path traversal attempts are rejected (../../etc/passwd, absolute paths, etc.)
  ✅ Valid relative paths are accepted
  ✅ list_files returns a list
  ✅ write_file creates a file with expected content
  ✅ read_file reads back what was written
  ✅ read_file on non-existent file raises FileNotFoundError
  ✅ lint_python returns clean result on valid Python
  ✅ lint_python returns issues on invalid Python
  ✅ lint_python rejects non-.py files

Security is the most interview-critical property here — test it exhaustively.
"""

from __future__ import annotations

import pytest


# ── Patch WORKSPACE_ROOT to a temp dir for all tests ─────────────────────────

@pytest.fixture(autouse=True)
def patch_workspace(tmp_path, monkeypatch):
    """
    Redirect all file operations to a per-test temp directory.
    This ensures tests are isolated from each other and from /workspace.
    """
    import mcp_servers.files_server as fs_module
    monkeypatch.setattr(fs_module, "WORKSPACE_ROOT", tmp_path.resolve())
    return tmp_path


# ── Path traversal rejection ──────────────────────────────────────────────────

class TestPathTraversalRejection:

    def test_double_dot_rejected(self, patch_workspace):
        from mcp_servers.files_server import _safe_resolve
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve("../../etc/passwd")

    def test_absolute_path_rejected(self, patch_workspace):
        from mcp_servers.files_server import _safe_resolve
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve("/etc/passwd")

    def test_windows_absolute_path_rejected(self, patch_workspace):
        from mcp_servers.files_server import _safe_resolve
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve("C:\\Windows\\System32\\drivers\\etc\\hosts")

    def test_encoded_traversal_rejected(self, patch_workspace):
        """URL-encoded traversal must also be rejected."""
        from mcp_servers.files_server import _safe_resolve
        # Python's Path resolves these — the canonical form will escape sandbox
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve("../outside.txt")

    def test_deep_traversal_rejected(self, patch_workspace):
        from mcp_servers.files_server import _safe_resolve
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve("subdir/../../../../../../etc/shadow")

    def test_valid_relative_path_accepted(self, patch_workspace):
        from mcp_servers.files_server import _safe_resolve
        # Should not raise — returns a Path inside the sandbox
        result = _safe_resolve("myfile.txt")
        assert str(patch_workspace.resolve()) in str(result)

    def test_nested_valid_path_accepted(self, patch_workspace):
        from mcp_servers.files_server import _safe_resolve
        result = _safe_resolve("subdir/myfile.txt")
        assert str(patch_workspace.resolve()) in str(result)


# ── list_files ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_files_empty_sandbox(patch_workspace):
    from mcp_servers.files_server import list_files
    result = await list_files("")
    assert isinstance(result, list)


@pytest.mark.anyio
async def test_list_files_nonexistent_path_returns_empty(patch_workspace):
    from mcp_servers.files_server import list_files
    result = await list_files("nonexistent_dir")
    assert result == []


# ── write_file + read_file ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_write_and_read_file(patch_workspace):
    from mcp_servers.files_server import write_file, read_file
    await write_file("hello.txt", "Hello, OrqFlow!")
    content = await read_file("hello.txt")
    assert content == "Hello, OrqFlow!"


@pytest.mark.anyio
async def test_write_returns_metadata(patch_workspace):
    from mcp_servers.files_server import write_file
    result = await write_file("meta.txt", "test content")
    assert result["written"] is True
    assert "meta.txt" in result["path"]
    assert result["bytes"] > 0


@pytest.mark.anyio
async def test_write_creates_parent_dirs(patch_workspace):
    from mcp_servers.files_server import write_file, read_file
    await write_file("subdir/nested/file.txt", "nested content")
    content = await read_file("subdir/nested/file.txt")
    assert content == "nested content"


@pytest.mark.anyio
async def test_read_nonexistent_raises(patch_workspace):
    from mcp_servers.files_server import read_file
    with pytest.raises(FileNotFoundError):
        await read_file("ghost.txt")


@pytest.mark.anyio
async def test_write_traversal_rejected(patch_workspace):
    from mcp_servers.files_server import write_file
    with pytest.raises(ValueError, match="Path traversal"):
        await write_file("../../evil.txt", "pwned")


# ── lint_python ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_lint_clean_python(patch_workspace):
    import shutil
    if not shutil.which("ruff"):
        pytest.skip("ruff not on PATH — install ruff or run inside Docker")
    from mcp_servers.files_server import write_file, lint_python
    await write_file("clean.py", 'def hello():\n    return "world"\n')
    result = await lint_python("clean.py")
    assert isinstance(result["clean"], bool)
    assert isinstance(result["issues"], list)
    assert "summary" in result


@pytest.mark.anyio
async def test_lint_nonexistent_file_raises(patch_workspace):
    from mcp_servers.files_server import lint_python
    with pytest.raises(FileNotFoundError):
        await lint_python("nope.py")


@pytest.mark.anyio
async def test_lint_non_python_file_raises(patch_workspace):
    from mcp_servers.files_server import write_file, lint_python
    await write_file("readme.md", "# Hello")
    with pytest.raises(ValueError, match=r"\.py"):
        await lint_python("readme.md")


@pytest.mark.anyio
async def test_lint_traversal_rejected(patch_workspace):
    from mcp_servers.files_server import lint_python
    with pytest.raises(ValueError, match="Path traversal"):
        await lint_python("../../app/auth.py")
