"""Tests for src/why/git_collector.py against the tiny_repo fixture."""

from __future__ import annotations

from pathlib import Path

from why.git_collector import (
    collect_commits,
    enrich_with_bodies,
    fetch_body,
    repo_remote_url,
)
from why.parse_target import parse_and_resolve


class TestCollectCommits:
    def test_whole_file_returns_all_commits(
        self, tiny_repo: Path, chdir_to
    ) -> None:
        chdir_to(tiny_repo)
        target = parse_and_resolve("app.py")
        commits = collect_commits(target)
        assert len(commits) == 3
        # newest first
        assert "greeting" in commits[0].subject.lower()

    def test_line_range_returns_subset(
        self, tiny_repo: Path, chdir_to
    ) -> None:
        chdir_to(tiny_repo)
        # Line 2 changed in commits 1 and 3 (initial + tweak greeting)
        target = parse_and_resolve("app.py:2")
        commits = collect_commits(target)
        assert len(commits) >= 1
        subjects = [c.subject for c in commits]
        # The "Tweak greeting" commit specifically touches line 2
        assert any("greeting" in s.lower() for s in subjects)

    def test_limit_caps_results(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        target = parse_and_resolve("app.py")
        commits = collect_commits(target, limit=2)
        assert len(commits) == 2

    def test_commits_have_required_fields(
        self, tiny_repo: Path, chdir_to
    ) -> None:
        chdir_to(tiny_repo)
        target = parse_and_resolve("app.py")
        c = collect_commits(target)[0]
        assert len(c.hash) == 40
        assert len(c.short) == 7
        assert c.author_name == "Test Author"
        assert c.author_email == "test@example.com"
        assert "T" in c.author_date  # ISO 8601 contains T
        assert c.subject


class TestEnrichWithBodies:
    def test_bodies_are_fetched(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        target = parse_and_resolve("app.py")
        commits = enrich_with_bodies(collect_commits(target))
        # At least one commit has a multi-line body (commit 2: "Fixes SUPPORT-1234.")
        bodied = [c for c in commits if c.body]
        assert len(bodied) >= 1
        assert any("SUPPORT-1234" in c.body for c in bodied)

    def test_refs_extracted_from_subject_and_body(
        self, tiny_repo: Path, chdir_to
    ) -> None:
        chdir_to(tiny_repo)
        target = parse_and_resolve("app.py")
        commits = enrich_with_bodies(collect_commits(target))

        # Commit 2: subject has "#42", body has "SUPPORT-1234" and "PR #42"
        commit2 = next(c for c in commits if "goodbye" in c.subject.lower())
        assert 42 in commit2.refs.pr_numbers
        assert "SUPPORT-1234" in commit2.refs.jira_keys

        # Commit 3: body has "Closes #99" + Jira "PROJ-7"
        commit3 = next(c for c in commits if "greeting" in c.subject.lower())
        assert 99 in commit3.refs.closes
        assert "PROJ-7" in commit3.refs.jira_keys


class TestFetchBody:
    def test_fetch_body_returns_post_subject_text(
        self, tiny_repo: Path, chdir_to
    ) -> None:
        chdir_to(tiny_repo)
        target = parse_and_resolve("app.py")
        commits = collect_commits(target)
        # Find the goodbye commit (which has a body)
        c = next(c for c in commits if "goodbye" in c.subject.lower())
        body = fetch_body(c.hash)
        assert "SUPPORT-1234" in body
        # Subject line should NOT be in body
        assert "Add goodbye function" not in body


class TestRepoRemoteUrl:
    def test_no_remote_returns_none(self, tiny_repo: Path, chdir_to) -> None:
        chdir_to(tiny_repo)
        # tiny_repo has no remote configured
        assert repo_remote_url() is None
