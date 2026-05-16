"""End-to-end CLI tests against the tiny_repo fixture."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest

from why.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    """Run main(argv) and return (exit_code, stdout, stderr)."""
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


class TestCliSuccess:
    def test_whole_file(
        self, tiny_repo: Path, chdir_to, capsys: pytest.CaptureFixture[str]
    ) -> None:
        chdir_to(tiny_repo)
        code, out, err = _run(["app.py", "--no-gh"], capsys)
        assert code == 0, err
        assert "# /why app.py" in out
        assert "Test Author" in out

    def test_single_line(
        self, tiny_repo: Path, chdir_to, capsys: pytest.CaptureFixture[str]
    ) -> None:
        chdir_to(tiny_repo)
        code, out, err = _run(["app.py:2", "--no-gh"], capsys)
        assert code == 0, err
        assert "app.py:2" in out

    def test_line_range(
        self, tiny_repo: Path, chdir_to, capsys: pytest.CaptureFixture[str]
    ) -> None:
        chdir_to(tiny_repo)
        code, out, err = _run(["app.py:1-3", "--no-gh"], capsys)
        assert code == 0, err
        assert "app.py:1-3" in out

    def test_limit(
        self, tiny_repo: Path, chdir_to, capsys: pytest.CaptureFixture[str]
    ) -> None:
        chdir_to(tiny_repo)
        code, out, err = _run(["app.py", "--limit", "1", "--no-gh"], capsys)
        assert code == 0, err
        # Only 1 commit should appear in the commit-list section
        commit_lines = [
            ln for ln in out.splitlines() if ln.startswith("- `")
        ]
        assert len(commit_lines) == 1


class TestCliFailures:
    def test_nonexistent_file(
        self, tiny_repo: Path, chdir_to, capsys: pytest.CaptureFixture[str]
    ) -> None:
        chdir_to(tiny_repo)
        code, out, err = _run(["does-not-exist.py", "--no-gh"], capsys)
        assert code == 2
        assert "File not found" in err

    def test_untracked_file(
        self, tiny_repo: Path, chdir_to, capsys: pytest.CaptureFixture[str]
    ) -> None:
        chdir_to(tiny_repo)
        (tiny_repo / "untracked.py").write_text("x = 1\n", encoding="utf-8")
        code, out, err = _run(["untracked.py", "--no-gh"], capsys)
        assert code == 2
        assert "not tracked by git" in err

    def test_line_beyond_eof(
        self, tiny_repo: Path, chdir_to, capsys: pytest.CaptureFixture[str]
    ) -> None:
        chdir_to(tiny_repo)
        code, out, err = _run(["app.py:9999", "--no-gh"], capsys)
        assert code == 2
        assert "beyond end of file" in err
