"""Pytest fixtures shared across the suite."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    """Build a deterministic tiny git repo on disk and return its path.

    The repo has 3 commits touching a single file `app.py`, with PR references
    in commit messages so PR-extraction tests have something to chew on.
    """
    repo = tmp_path / "tiny-repo"
    repo.mkdir()

    def git(*args: str, cwd: Path = repo) -> str:
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test Author",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "GIT_AUTHOR_DATE": "2024-01-01T12:00:00+00:00",
            "GIT_COMMITTER_DATE": "2024-01-01T12:00:00+00:00",
        }
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return result.stdout

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test Author")
    git("config", "commit.gpgsign", "false")

    app = repo / "app.py"

    # Commit 1 — initial file
    app.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    git("add", "app.py")
    git("commit", "-q", "-m", "Initial commit (#1)")

    # Commit 2 — add a function, with PR refs
    app.write_text(
        "def hello():\n"
        "    return 'world'\n"
        "\n"
        "def goodbye():\n"
        "    return 'farewell'\n",
        encoding="utf-8",
    )
    git("add", "app.py")
    git(
        "commit",
        "-q",
        "-m",
        "Add goodbye function (#42)\n\nFixes SUPPORT-1234. See PR #42 for context.",
    )

    # Commit 3 — modify line 2, with closes-keyword
    app.write_text(
        "def hello():\n"
        "    return 'planet'\n"
        "\n"
        "def goodbye():\n"
        "    return 'farewell'\n",
        encoding="utf-8",
    )
    git("add", "app.py")
    git(
        "commit",
        "-q",
        "-m",
        "Tweak greeting wording\n\nCloses #99 — feedback from PROJ-7.",
    )

    return repo


@pytest.fixture
def chdir_to(monkeypatch: pytest.MonkeyPatch):
    """Helper to change CWD for a single test."""

    def _chdir(path: Path) -> None:
        monkeypatch.chdir(path)

    return _chdir
