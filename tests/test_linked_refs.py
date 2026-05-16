"""Tests for src/why/linked_refs.py."""

from __future__ import annotations

from why.linked_refs import LinkedRefs, extract, merge


class TestExtractPRNumbers:
    def test_bare_pr_ref(self) -> None:
        assert extract("see #123 for context").pr_numbers == [123]

    def test_pr_in_parens(self) -> None:
        assert extract("Fix the bug (#42)").pr_numbers == [42]

    def test_multiple_prs_deduped_preserving_order(self) -> None:
        text = "Combines #1, #2, and a follow-up to #1"
        assert extract(text).pr_numbers == [1, 2]

    def test_does_not_match_hash_prefixes(self) -> None:
        # Hash-like strings should not produce a PR number match
        assert extract("commit #deadbeef something").pr_numbers == []

    def test_does_not_match_long_numbers(self) -> None:
        # 8+ digit numbers aren't realistic PR/issue numbers
        assert extract("see #12345678 here").pr_numbers == []

    def test_empty_input(self) -> None:
        assert extract("").pr_numbers == []
        assert extract(None).pr_numbers == []


class TestExtractJira:
    def test_basic_jira(self) -> None:
        assert extract("Fixes SUPPORT-1234").jira_keys == ["SUPPORT-1234"]

    def test_multiple_projects(self) -> None:
        refs = extract("Fixes PROJ-1 and BUG-99, related to PROJ-1")
        assert refs.jira_keys == ["PROJ-1", "BUG-99"]

    def test_does_not_match_hash_like(self) -> None:
        # We require leading boundary — "MD5-1" should match (it's a valid
        # 3-char project key); but "abcMD5-1" shouldn't.
        assert "MD5-1" not in extract("see abcMD5-1 here").jira_keys

    def test_requires_uppercase_project(self) -> None:
        # Lowercase project keys shouldn't match
        assert extract("see proj-123 here").jira_keys == []


class TestExtractCloses:
    def test_closes_keyword(self) -> None:
        for prefix in ["Closes", "closes", "fixes", "Resolved", "Fix"]:
            refs = extract(f"{prefix} #42")
            assert 42 in refs.closes, f"{prefix} should be recognized"

    def test_closes_with_repo_qualifier(self) -> None:
        refs = extract("Closes acme/repo#45")
        assert 45 in refs.closes

    def test_closes_dedupes(self) -> None:
        refs = extract("Closes #1. Also closes #1.")
        assert refs.closes == [1]

    def test_no_keyword_no_closes(self) -> None:
        # Bare "#1" isn't a closes ref
        assert extract("See #1").closes == []
        # But it should still appear in pr_numbers
        assert extract("See #1").pr_numbers == [1]


class TestMerge:
    def test_merge_dedupes_across_lists(self) -> None:
        a = LinkedRefs(pr_numbers=[1, 2], jira_keys=["X-1"], closes=[1])
        b = LinkedRefs(pr_numbers=[2, 3], jira_keys=["X-1", "Y-2"], closes=[3])
        m = merge([a, b])
        assert m.pr_numbers == [1, 2, 3]
        assert m.jira_keys == ["X-1", "Y-2"]
        assert m.closes == [1, 3]

    def test_merge_empty(self) -> None:
        m = merge([])
        assert m.is_empty()


class TestLinkedRefs:
    def test_is_empty(self) -> None:
        assert LinkedRefs().is_empty()
        assert not LinkedRefs(pr_numbers=[1]).is_empty()
