"""Render the gathered context as a structured Markdown bundle for in-session Claude."""

from __future__ import annotations

from why.git_collector import Commit
from why.gh_collector import GhStatus, PullRequest
from why.linked_refs import LinkedRefs, merge
from why.parse_target import Target


def _format_commit_line(c: Commit) -> str:
    """One-line summary of a commit for the 'Commits that touched it' list."""
    pr_hint = ""
    if c.refs.pr_numbers:
        pr_hint = " [PR " + ", ".join(f"#{n}" for n in c.refs.pr_numbers) + "]"
    return (
        f"- `{c.short}` {c.author_name} <{c.author_email}> {c.author_date} "
        f'"{c.subject}"{pr_hint}'
    )


def _format_pr_block(pr: PullRequest) -> str:
    lines = [
        f"### PR #{pr.number} — {pr.title}",
        f"- **Author:** {pr.author or '(unknown)'}",
        f"- **Created:** {pr.created_at or '(unknown)'}",
    ]
    if pr.closing_issues:
        lines.append(f"- **Closes:** {', '.join(pr.closing_issues)}")
    if pr.body:
        lines.append("")
        lines.append("**Body:**")
        lines.append("")
        # Indent the body so it's clearly attributed and harder for the model
        # to mistake for plugin instructions.
        for body_line in pr.body.splitlines():
            lines.append(f"> {body_line}" if body_line.strip() else ">")
    else:
        lines.append("")
        lines.append("**Body:** (empty)")
    return "\n".join(lines)


def render(
    target: Target,
    commits: list[Commit],
    prs: dict[int, PullRequest],
    gh_status: GhStatus,
    remote_url: str | None = None,
) -> str:
    """Assemble the final Markdown bundle written to stdout.

    The format is consumed by the in-session Claude that runs after the slash
    command — keep the section headers stable; the prompt in `.claude/commands/
    why.md` references them.
    """
    lines: list[str] = []

    # --- Header
    lines.append(f"# /why {target.display}")
    lines.append("")
    lines.append(f"**Target:** `{target.display}`")
    if remote_url:
        lines.append(f"**Repo:** {remote_url}")
    if gh_status.available:
        if gh_status.account:
            lines.append(f"**`gh` account:** {gh_status.account}")
        else:
            lines.append("**`gh`:** available")
    else:
        lines.append(f"**`gh`:** not available — {gh_status.reason}")
    lines.append("")

    # --- Commits
    lines.append("## Commits that touched it (newest first)")
    lines.append("")
    if not commits:
        lines.append("_No commits found in history for this target._")
        lines.append("")
        lines.append(
            "This is unusual — most committed files have at least one commit. "
            "If this is a newly added file, the user's working copy may not match HEAD."
        )
    else:
        for c in commits:
            lines.append(_format_commit_line(c))

    lines.append("")

    # --- Commit bodies (full text, for any commit that has one)
    bodied = [c for c in commits if c.body.strip()]
    if bodied:
        lines.append("## Commit messages (full text)")
        lines.append("")
        for c in bodied:
            lines.append(f"### `{c.short}` — {c.subject}")
            for body_line in c.body.splitlines():
                lines.append(f"> {body_line}" if body_line.strip() else ">")
            lines.append("")

    # --- Pull requests
    all_pr_numbers: list[int] = []
    seen_pr: set[int] = set()
    for c in commits:
        for n in c.refs.pr_numbers:
            if n not in seen_pr:
                seen_pr.add(n)
                all_pr_numbers.append(n)

    if all_pr_numbers:
        lines.append("## Pull requests referenced")
        lines.append("")
        if not gh_status.available:
            lines.append(
                "_`gh` is not available, so PR descriptions weren't fetched. "
                "The narrative should mention this and recommend installing `gh` "
                "for richer output next time._"
            )
            lines.append("")
            lines.append(
                "Referenced PRs (numbers only): "
                + ", ".join(f"#{n}" for n in all_pr_numbers)
            )
            lines.append("")
        else:
            fetched = []
            missing = []
            for n in all_pr_numbers:
                if n in prs:
                    fetched.append(n)
                else:
                    missing.append(n)
            for n in fetched:
                lines.append(_format_pr_block(prs[n]))
                lines.append("")
            if missing:
                lines.append(
                    "_The following PR numbers were referenced in commits but "
                    "could not be fetched (private, deleted, or cross-repo): "
                    + ", ".join(f"#{n}" for n in missing)
                    + "._"
                )
                lines.append("")

    # --- Linked tickets / issues (Jira-style + closes-keyword refs)
    all_refs: LinkedRefs = merge(
        [c.refs for c in commits] + [pr.refs for pr in prs.values()]
    )
    if all_refs.jira_keys or all_refs.closes:
        lines.append("## Linked tickets and issues")
        lines.append("")
        if all_refs.jira_keys:
            lines.append(
                "- **Ticket refs:** " + ", ".join(all_refs.jira_keys)
            )
        if all_refs.closes:
            closing_strs = ", ".join(f"#{n}" for n in all_refs.closes)
            lines.append(f"- **Explicitly closed by these PRs:** {closing_strs}")
        lines.append("")

    # --- Grounding rules — repeat them right next to the data the narrative
    # will be built from. Defense in depth alongside the slash command prompt.
    lines.append("## Grounding rules for the narrative")
    lines.append("")
    lines.append(
        "1. Every factual claim must cite a commit hash, PR number, "
        "or ticket ID from the data above."
    )
    lines.append(
        "2. If the data doesn't support a claim, do not make it. "
        '"The history doesn\'t say why" is a valid and preferred answer.'
    )
    lines.append(
        "3. Distinguish observation (the PR body literally says X) "
        "from inference (the subject suggests X)."
    )
    lines.append(
        "4. Do not name files, functions, or symbols not present "
        "in the data above."
    )
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
