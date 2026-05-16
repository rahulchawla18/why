"""Command-line entrypoint for /why.

Invoked by the slash command as:
    python -m why.cli "<target>"

Prints the structured Markdown bundle to stdout. Returns non-zero on errors,
with a user-friendly message on stderr.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from why import __version__
from why.git_collector import (
    GitError,
    collect_commits,
    enrich_with_bodies,
    repo_remote_url,
)
from why.gh_collector import detect as detect_gh
from why.gh_collector import fetch_prs
from why.parse_target import TargetError, parse_and_resolve
from why.render import render


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="why",
        description=(
            "Gather git and PR history for a file or line range. "
            "Prints a structured Markdown bundle for an LLM to summarize."
        ),
    )
    p.add_argument(
        "target",
        help="<file>, <file>:<line>, or <file>:<start>-<end>",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of commits to gather (default: all).",
    )
    p.add_argument(
        "--no-gh",
        action="store_true",
        help="Skip GitHub PR fetching even if gh is installed.",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # --- Resolve the target
    try:
        target = parse_and_resolve(args.target)
    except TargetError as e:
        print(f"why: {e}", file=sys.stderr)
        return 2

    # --- Gather commits
    try:
        commits = collect_commits(target, limit=args.limit)
        enrich_with_bodies(commits)
    except GitError as e:
        print(f"why: {e}", file=sys.stderr)
        return 3

    # --- Detect gh, fetch referenced PRs (if available)
    if args.no_gh:
        from why.gh_collector import GhStatus
        gh_status = GhStatus(available=False, reason="disabled via --no-gh")
    else:
        gh_status = detect_gh()

    prs: dict[int, "object"] = {}  # type: ignore[assignment]
    if gh_status.available:
        # Collect referenced PR numbers across all commits, preserving order.
        seen: set[int] = set()
        numbers: list[int] = []
        for c in commits:
            for n in c.refs.pr_numbers:
                if n not in seen:
                    seen.add(n)
                    numbers.append(n)
        prs = fetch_prs(numbers)  # type: ignore[assignment]

    # --- Render and print
    remote = repo_remote_url()
    output = render(
        target=target,
        commits=commits,
        prs=prs,  # type: ignore[arg-type]
        gh_status=gh_status,
        remote_url=remote,
    )
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
