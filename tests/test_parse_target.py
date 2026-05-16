"""Tests for src/why/parse_target.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from why.parse_target import (
    Target,
    TargetError,
    parse,
    parse_and_resolve,
    resolve,
)


class TestParse:
    def test_whole_file(self) -> None:
        assert parse("app.py") == ("app.py", None, None)

    def test_single_line(self) -> None:
        assert parse("app.py:42") == ("app.py", 42, 42)

    def test_line_range(self) -> None:
        assert parse("src/auth.ts:10-20") == ("src/auth.ts", 10, 20)

    def test_strips_whitespace(self) -> None:
        assert parse("  app.py:5  ") == ("app.py", 5, 5)

    def test_empty_raises(self) -> None:
        with pytest.raises(TargetError, match="No target provided"):
            parse("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(TargetError, match="No target provided"):
            parse("   ")

    def test_negative_line_raises(self) -> None:
        # "-5" is parsed as path "app.py:-5" → no range match → whole-file path
        # Negative numbers in a range *suffix* should be rejected though.
        with pytest.raises(TargetError, match="positive"):
            # 0 is treated as positive-int regex match, then fails the check
            parse("app.py:0")

    def test_inverted_range_raises(self) -> None:
        with pytest.raises(TargetError, match="before start"):
            parse("app.py:20-10")

    def test_windows_drive_path_treated_as_path(self) -> None:
        # "C:\foo.py" has a colon but no valid range suffix — should be path
        path, start, end = parse("C:\\foo.py")
        assert path == "C:\\foo.py"
        assert start is None and end is None

    def test_colon_in_filename_without_range_suffix(self) -> None:
        # weird:filename has a colon but no digits → treat as whole path
        path, start, end = parse("weird:filename")
        assert path == "weird:filename"
        assert start is None and end is None


class TestResolve:
    def test_whole_file_in_tiny_repo(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        t = resolve("app.py", None, None)
        assert t == Target(path="app.py", line_start=None, line_end=None)
        assert t.is_whole_file
        assert t.display == "app.py"

    def test_line_in_tiny_repo(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        t = resolve("app.py", 1, 1)
        assert t.line_start == 1 and t.line_end == 1
        assert t.display == "app.py:1"

    def test_range_in_tiny_repo(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        t = resolve("app.py", 1, 3)
        assert t.display == "app.py:1-3"

    def test_clamps_end_to_file_length(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        # app.py has 5 lines. Asking for 1-9999 should clamp end to 5.
        t = resolve("app.py", 1, 9999)
        assert t.line_end == 5

    def test_start_beyond_file_raises(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        with pytest.raises(TargetError, match="beyond end of file"):
            resolve("app.py", 100, 100)

    def test_nonexistent_file_raises(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        with pytest.raises(TargetError, match="File not found"):
            resolve("does-not-exist.py", None, None)

    def test_untracked_file_raises(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        (tiny_repo / "untracked.py").write_text("x = 1\n", encoding="utf-8")
        with pytest.raises(TargetError, match="not tracked by git"):
            resolve("untracked.py", None, None)

    def test_directory_raises(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        with pytest.raises(TargetError, match="is a directory"):
            resolve(".", None, None)


class TestParseAndResolve:
    def test_e2e_whole_file(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        t = parse_and_resolve("app.py")
        assert t.is_whole_file

    def test_e2e_range(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        t = parse_and_resolve("app.py:1-2")
        assert t.line_start == 1
        assert t.line_end == 2
