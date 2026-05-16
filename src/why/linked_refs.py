"""Extract PR numbers, ticket IDs, and issue refs from commit messages and PR bodies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# `(#123)` or `#123` in commit subjects, PR descriptions, comments.
# We require word-boundary + a digit to avoid matching things like `#deadbeef`
# or markdown anchors. The number must be 1-7 digits — PR/issue numbers fit.
_PR_RE = re.compile(r"(?<![A-Za-z0-9_])#(\d{1,7})\b")

# Jira-style "PROJ-123". Project key is 2-10 uppercase letters; ID is 1-7 digits.
# We anchor with word boundaries to avoid matching things like `MD5-1` in a hash.
_JIRA_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-(\d{1,7})\b")

# GitHub closes-keyword forms: "Closes #123", "Fixes acme/repo#45"
# We pull the bare number out — the PR_RE already covers #123, but this lets
# us tag it as "explicitly closes" for the renderer if we ever want to.
_CLOSES_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:[\w./-]+)?#(\d{1,7})\b",
    re.IGNORECASE,
)


@dataclass
class LinkedRefs:
    """Refs extracted from a piece of text."""

    pr_numbers: list[int] = field(default_factory=list)
    jira_keys: list[str] = field(default_factory=list)  # e.g. "SUPPORT-1234"
    closes: list[int] = field(default_factory=list)     # PR numbers explicitly closed

    def is_empty(self) -> bool:
        return not (self.pr_numbers or self.jira_keys or self.closes)


def extract(text: str | None) -> LinkedRefs:
    """Extract refs from `text`. Returns an empty LinkedRefs for empty/None input.

    Each list is deduplicated while preserving first-seen order.
    """
    if not text:
        return LinkedRefs()

    seen_pr: set[int] = set()
    pr_numbers: list[int] = []
    for m in _PR_RE.finditer(text):
        n = int(m.group(1))
        if n not in seen_pr:
            seen_pr.add(n)
            pr_numbers.append(n)

    seen_jira: set[str] = set()
    jira_keys: list[str] = []
    for m in _JIRA_RE.finditer(text):
        key = f"{m.group(1)}-{m.group(2)}"
        if key not in seen_jira:
            seen_jira.add(key)
            jira_keys.append(key)

    seen_close: set[int] = set()
    closes: list[int] = []
    for m in _CLOSES_RE.finditer(text):
        n = int(m.group(1))
        if n not in seen_close:
            seen_close.add(n)
            closes.append(n)

    return LinkedRefs(pr_numbers=pr_numbers, jira_keys=jira_keys, closes=closes)


def merge(refs_list: list[LinkedRefs]) -> LinkedRefs:
    """Combine multiple LinkedRefs into one, deduplicating in order."""
    merged = LinkedRefs()
    seen_pr: set[int] = set()
    seen_jira: set[str] = set()
    seen_close: set[int] = set()
    for r in refs_list:
        for n in r.pr_numbers:
            if n not in seen_pr:
                seen_pr.add(n)
                merged.pr_numbers.append(n)
        for k in r.jira_keys:
            if k not in seen_jira:
                seen_jira.add(k)
                merged.jira_keys.append(k)
        for n in r.closes:
            if n not in seen_close:
                seen_close.add(n)
                merged.closes.append(n)
    return merged
