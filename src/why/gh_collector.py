"""Fetch PR descriptions via the `gh` CLI, with graceful degradation when absent."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field

from why.linked_refs import LinkedRefs, extract


@dataclass
class PullRequest:
    """A pull request resolved via `gh pr view`."""

    number: int
    title: str
    body: str
    author: str
    created_at: str          # ISO 8601
    closing_issues: list[str] = field(default_factory=list)
    refs: LinkedRefs = field(default_factory=LinkedRefs)


@dataclass
class GhStatus:
    """Whether the `gh` CLI is available and usable for PR fetches."""

    available: bool
    reason: str = ""         # Human-readable explanation if not available
    account: str | None = None  # The authenticated GitHub username, if known


def detect() -> GhStatus:
    """Check whether `gh` is installed and authenticated.

    Returns a GhStatus. The plugin still works when `gh` is unavailable — this
    just lets the renderer note "PR data not fetched, install gh for richer
    narratives."
    """
    binary = shutil.which("gh")
    if not binary:
        return GhStatus(
            available=False,
            reason="gh CLI not installed. See https://cli.github.com to install.",
        )

    # `gh auth status` exits 0 when authenticated. We capture stderr because
    # gh prints account info there in older versions.
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return GhStatus(available=False, reason=f"gh auth check failed: {e}")

    if result.returncode != 0:
        return GhStatus(
            available=False,
            reason="gh is installed but not authenticated. Run `gh auth login`.",
        )

    # Try to extract the account username for the audit-trail note.
    # gh prints lines like "  Logged in to github.com as username (..."
    combined = (result.stdout or "") + (result.stderr or "")
    account = None
    for line in combined.splitlines():
        stripped = line.strip()
        if "Logged in to" in stripped and " as " in stripped:
            try:
                account = stripped.split(" as ", 1)[1].split(" ", 1)[0].rstrip("()")
            except IndexError:
                account = None
            break

    return GhStatus(available=True, account=account)


def fetch_pr(number: int) -> PullRequest | None:
    """Fetch a single PR by number. Returns None on any error.

    Errors are intentionally swallowed: one missing/private PR shouldn't break
    the whole narrative. The renderer will note which PRs were referenced but
    not fetched.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                str(number),
                "--json",
                "number,title,body,author,createdAt,closingIssuesReferences",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    # gh returns `author` as {"login": "...", ...}
    author_field = data.get("author") or {}
    author = author_field.get("login", "") if isinstance(author_field, dict) else ""

    body = data.get("body") or ""
    refs = extract(f"{data.get('title', '')}\n{body}")

    closing = []
    for issue in data.get("closingIssuesReferences") or []:
        if isinstance(issue, dict) and issue.get("number") is not None:
            # gh returns just `{number, title, url}` for cross-repo issues;
            # we keep the raw "#N" form since the narrative just cites it.
            closing.append(f"#{issue['number']}")

    return PullRequest(
        number=data.get("number", number),
        title=data.get("title", ""),
        body=body,
        author=author,
        created_at=data.get("createdAt", ""),
        closing_issues=closing,
        refs=refs,
    )


def fetch_prs(numbers: list[int]) -> dict[int, PullRequest]:
    """Fetch many PRs. Failures are silently dropped — caller can diff the
    requested set against the returned dict to see what was missed.
    """
    out: dict[int, PullRequest] = {}
    for n in numbers:
        pr = fetch_pr(n)
        if pr is not None:
            out[n] = pr
    return out
