"""Tests for src/why/render.py — focused on output structure, not narrative quality."""

from __future__ import annotations

from why.git_collector import Commit
from why.gh_collector import GhStatus, PullRequest
from why.linked_refs import LinkedRefs
from why.parse_target import Target
from why.render import render


def _make_commit(
    short: str = "a1b2c3d",
    subject: str = "Fix bug",
    body: str = "",
    refs: LinkedRefs | None = None,
) -> Commit:
    return Commit(
        hash=short + "0" * (40 - len(short)),
        short=short,
        author_name="Alice",
        author_email="alice@example.com",
        author_date="2024-01-15T10:30:00+00:00",
        subject=subject,
        body=body,
        refs=refs or LinkedRefs(),
    )


class TestRenderStructure:
    def test_has_required_sections(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        out = render(
            target=target,
            commits=[_make_commit()],
            prs={},
            gh_status=GhStatus(available=True),
        )
        assert "# /why app.py" in out
        assert "## Commits that touched it" in out
        assert "## Grounding rules for the narrative" in out

    def test_header_includes_target_display(self) -> None:
        target = Target(path="app.py", line_start=10, line_end=20)
        out = render(
            target=target,
            commits=[],
            prs={},
            gh_status=GhStatus(available=True),
        )
        assert "app.py:10-20" in out

    def test_no_commits_is_handled(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        out = render(
            target=target,
            commits=[],
            prs={},
            gh_status=GhStatus(available=True),
        )
        assert "No commits found" in out

    def test_commit_line_includes_hash_author_date_subject(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        c = _make_commit(short="abcdef1", subject="Hello world")
        out = render(
            target=target,
            commits=[c],
            prs={},
            gh_status=GhStatus(available=True),
        )
        assert "abcdef1" in out
        assert "Alice" in out
        assert "alice@example.com" in out
        assert "2024-01-15T10:30:00+00:00" in out
        assert "Hello world" in out


class TestGhAvailability:
    def test_gh_unavailable_message(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        out = render(
            target=target,
            commits=[],
            prs={},
            gh_status=GhStatus(available=False, reason="gh CLI not installed"),
        )
        assert "not available" in out
        assert "gh CLI not installed" in out

    def test_gh_unavailable_with_pr_refs_lists_them(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        c = _make_commit(refs=LinkedRefs(pr_numbers=[42, 99]))
        out = render(
            target=target,
            commits=[c],
            prs={},
            gh_status=GhStatus(available=False, reason="no gh"),
        )
        assert "#42" in out
        assert "#99" in out
        assert "PR descriptions weren't fetched" in out

    def test_gh_account_shown_when_available(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        out = render(
            target=target,
            commits=[],
            prs={},
            gh_status=GhStatus(available=True, account="alice"),
        )
        assert "alice" in out


class TestPRRendering:
    def test_fetched_pr_body_included(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        c = _make_commit(refs=LinkedRefs(pr_numbers=[42]))
        pr = PullRequest(
            number=42,
            title="Fix the SSO race",
            body="Customers reported sessions being reused across logins.",
            author="bob",
            created_at="2024-01-10T09:00:00+00:00",
        )
        out = render(
            target=target,
            commits=[c],
            prs={42: pr},
            gh_status=GhStatus(available=True),
        )
        assert "PR #42 — Fix the SSO race" in out
        assert "Customers reported sessions being reused" in out
        assert "bob" in out

    def test_missing_pr_is_noted(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        c = _make_commit(refs=LinkedRefs(pr_numbers=[42, 99]))
        # Only #42 was fetched; #99 should appear in the "missing" list
        pr = PullRequest(
            number=42, title="X", body="", author="", created_at=""
        )
        out = render(
            target=target,
            commits=[c],
            prs={42: pr},
            gh_status=GhStatus(available=True),
        )
        assert "could not be fetched" in out
        assert "#99" in out


class TestLinkedTickets:
    def test_jira_refs_listed(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        c = _make_commit(refs=LinkedRefs(jira_keys=["SUPPORT-1234"]))
        out = render(
            target=target,
            commits=[c],
            prs={},
            gh_status=GhStatus(available=False, reason="x"),
        )
        assert "SUPPORT-1234" in out
        assert "## Linked tickets and issues" in out

    def test_closes_refs_listed(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        c = _make_commit(refs=LinkedRefs(closes=[99]))
        out = render(
            target=target,
            commits=[c],
            prs={},
            gh_status=GhStatus(available=False, reason="x"),
        )
        assert "Explicitly closed" in out
        assert "#99" in out


class TestGroundingRules:
    def test_rules_present_in_output(self) -> None:
        target = Target(path="app.py", line_start=None, line_end=None)
        out = render(
            target=target,
            commits=[],
            prs={},
            gh_status=GhStatus(available=True),
        )
        # Spot-check the four rules
        assert "cite a commit hash" in out.lower()
        assert "do not make it" in out
        assert "observation" in out and "inference" in out
        assert "not present" in out
