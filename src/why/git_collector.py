"""Gather commit history for a Target from the local git repo."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from why.linked_refs import LinkedRefs, extract
from why.parse_target import Target

# Field separator unlikely to appear in a real commit field.
# `git log --pretty` doesn't interpolate this from input — it's a literal.
_SEP = "\x1f"  # ASCII unit separator
_PRETTY = f"%H{_SEP}%an{_SEP}%ae{_SEP}%aI{_SEP}%s"


class GitError(RuntimeError):
    """Raised when git itself fails in a way we can't recover from."""


@dataclass
class Commit:
    """One commit that touched the target."""

    hash: str          # full 40-char SHA
    short: str         # 7-char prefix for display
    author_name: str
    author_email: str
    author_date: str   # ISO 8601
    subject: str
    body: str = ""     # full commit message body (subject excluded)
    refs: LinkedRefs = field(default_factory=LinkedRefs)


def _run_git(args: list[str]) -> str:
    """Run a git command and return stdout. Raises GitError on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as e:
        raise GitError("git is not installed or not on PATH") from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise GitError(f"git {' '.join(args)} failed: {stderr}") from e
    return result.stdout


def _parse_log_lines(stdout: str) -> list[Commit]:
    """Parse `git log --pretty=<our format>` stdout into Commit objects (no body)."""
    commits: list[Commit] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(_SEP)
        if len(parts) < 5:
            # Malformed line — skip rather than crash. Real git output won't
            # produce this; only embedded separator characters could.
            continue
        h, name, email, date, subject = parts[0], parts[1], parts[2], parts[3], parts[4]
        commits.append(
            Commit(
                hash=h,
                short=h[:7],
                author_name=name,
                author_email=email,
                author_date=date,
                subject=subject,
            )
        )
    return commits


def collect_commits(target: Target, limit: int | None = None) -> list[Commit]:
    """Collect commits that touched the target, newest first.

    For line-ranged targets uses `git log -L<start>,<end>:<path>`. For whole
    files uses `git log --follow` so rename history is preserved.
    """
    if target.is_whole_file:
        # --follow only works with a single path arg
        args = [
            "log",
            "--follow",
            f"--pretty=format:{_PRETTY}",
            "--no-patch",
            "--",
            target.path,
        ]
    else:
        # git log -L<start>,<end>:<path> emits commit headers AND patches.
        # `--no-patch` does NOT work with -L (git rejects it). Instead we use
        # `-s` (silent / suppress diff output) which IS honored by -L.
        start = target.line_start
        end = target.line_end or target.line_start
        args = [
            "log",
            f"-L{start},{end}:{target.path}",
            f"--pretty=format:{_PRETTY}",
            "-s",
        ]

    if limit is not None and limit > 0:
        args.insert(1, f"-n{limit}")

    stdout = _run_git(args)
    return _parse_log_lines(stdout)


def fetch_body(commit_hash: str) -> str:
    """Fetch the body (post-subject text) of a commit."""
    # %b = body only (subject excluded). Trailing newline trimmed.
    stdout = _run_git(["show", "-s", "--format=%b", commit_hash])
    return stdout.strip()


def enrich_with_bodies(commits: list[Commit]) -> list[Commit]:
    """For each commit, fetch its body and extract linked refs.

    Mutates the input list in place AND returns it for convenience.
    """
    for c in commits:
        c.body = fetch_body(c.hash)
        # Refs come from subject + body — PR refs sometimes only appear in the
        # subject (e.g. "Fix race (#847)") and sometimes only in the body.
        c.refs = extract(f"{c.subject}\n{c.body}")
    return commits


def repo_remote_url() -> str | None:
    """Best-effort fetch of the origin URL. Returns None if no origin is set."""
    try:
        out = _run_git(["config", "--get", "remote.origin.url"]).strip()
        return out or None
    except GitError:
        return None
