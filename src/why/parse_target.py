"""Parse the user's /why argument into a Target the rest of the pipeline understands."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class TargetError(ValueError):
    """Raised when a user-supplied target cannot be resolved."""


@dataclass(frozen=True)
class Target:
    """A resolved /why target.

    `path` is the file path as the user typed it (also valid as a git path).
    `line_start` and `line_end` are 1-indexed and inclusive. When both are None,
    the target is the whole file.
    """

    path: str
    line_start: int | None
    line_end: int | None

    @property
    def is_whole_file(self) -> bool:
        return self.line_start is None and self.line_end is None

    @property
    def display(self) -> str:
        if self.is_whole_file:
            return self.path
        if self.line_end is None or self.line_end == self.line_start:
            return f"{self.path}:{self.line_start}"
        return f"{self.path}:{self.line_start}-{self.line_end}"


# Accept:  path
#          path:N
#          path:N-M
# We split on the LAST colon so Windows drive letters in paths still work.
_RANGE_RE = re.compile(r"^(\d+)(?:-(\d+))?$")


def parse(arg: str) -> tuple[str, int | None, int | None]:
    """Parse a raw argument string into (path, line_start, line_end).

    Pure string parsing — no filesystem or git calls. Use `resolve()` to validate.
    """
    if not arg or not arg.strip():
        raise TargetError("No target provided. Usage: /why <file>[:<line>|:<start>-<end>]")

    arg = arg.strip()

    # Look for a `:N` or `:N-M` suffix. We split on the last colon so paths
    # containing colons (Windows drives, weird filenames) still parse.
    if ":" in arg:
        head, _, tail = arg.rpartition(":")
        m = _RANGE_RE.match(tail)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else start
            if start <= 0 or end <= 0:
                raise TargetError(f"Line numbers must be positive: got {tail!r}")
            if end < start:
                raise TargetError(
                    f"Line range end ({end}) is before start ({start})"
                )
            return head, start, end
        # Colon in arg but no valid range suffix — treat whole thing as path
        # (avoids breaking Windows paths like C:\foo or paths with colons in
        # filenames). Resolution will catch nonexistent paths later.
    return arg, None, None


def resolve(path: str, line_start: int | None, line_end: int | None) -> Target:
    """Validate the target exists in the current repo and return a Target.

    Raises TargetError with a user-friendly message on any failure.
    """
    p = Path(path)
    if not p.exists():
        raise TargetError(
            f"File not found: {path!r}. Path must be relative to the current "
            f"directory or absolute."
        )
    if p.is_dir():
        raise TargetError(f"{path!r} is a directory, not a file.")

    # Ensure we're in a git repo and the file is tracked.
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(p)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise TargetError("git is not installed or not on PATH") from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        if "not a git repository" in stderr.lower():
            raise TargetError(
                "Not inside a git repository. /why needs git history to work."
            ) from e
        raise TargetError(
            f"File {path!r} is not tracked by git. /why can only explain "
            f"committed code. (git says: {stderr or 'unknown reason'})"
        ) from e

    # Bound line numbers by file length (only matters for line targets).
    if line_start is not None:
        try:
            # Read line count without slurping the whole file into memory.
            with p.open("rb") as f:
                file_lines = sum(1 for _ in f)
        except OSError as e:
            raise TargetError(f"Could not read {path!r}: {e}") from e
        if line_start > file_lines:
            raise TargetError(
                f"Line {line_start} is beyond end of file ({file_lines} lines)."
            )
        # Clamp end silently — user asking for :40-9999 on a 50-line file is
        # most likely a typo for "from 40 to end."
        if line_end is not None and line_end > file_lines:
            line_end = file_lines

    return Target(path=str(p), line_start=line_start, line_end=line_end)


def parse_and_resolve(arg: str) -> Target:
    """Convenience: parse() then resolve()."""
    path, start, end = parse(arg)
    return resolve(path, start, end)
