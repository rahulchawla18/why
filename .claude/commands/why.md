---
name: why
description: Explain why a piece of code exists, using real git history and PR data. Usage - /why <file>[:<line>|:<start>-<end>]
argument-hint: <file>[:<line>|:<start>-<end>]
---

# /why — Code Archaeology

The user wants to know why a specific piece of code exists.

## Step 1 — Gather the history

Run the data-gathering script with the user's argument:

```bash
python -m why.cli "$ARGUMENTS"
```

The script prints a structured Markdown bundle to stdout containing:

- **Code in question** — the file and line range under investigation
- **Commits that touched it** — newest first, with hash, author, date, subject, and any referenced PR numbers
- **Pull request details** — if `gh` is available, title and body of each referenced PR
- **Linked issues / tickets** — any `#N`, `JIRA-456`, `SUPPORT-1234`-style refs found in commit messages and PR bodies

If the script exits non-zero, surface its stderr to the user verbatim — common failures are "file not tracked by git" or "no git repository here." Do not attempt to write a narrative when the data-gathering step failed.

## Step 2 — Write the narrative

Read the script's stdout carefully, then write a **2-paragraph narrative** explaining why this code exists.

### Grounding rules (these are non-negotiable)

1. **Cite a commit hash, PR number, or file path for every factual claim.** A claim without a citation is a claim you must not make.
2. **Do not invent context.** If the gathered data doesn't mention a customer escalation, a ticket, or a reason — do not say there was one. The honest answer "the history doesn't say why" is better than a made-up reason.
3. **Distinguish observation from inference.** If the PR body literally says "fixes the SSO race," report that. If you're inferring intent from a commit subject like "tweak auth flow," say so: *"the commit message suggests..."*, not *"this was done to..."*.
4. **Do not name files, functions, or symbols that aren't in the gathered context.** No invented filenames. No invented function names.
5. **If the history is sparse** (one commit, no PR, terse message), say so plainly: *"This was added in commit a1b2c3d with the message 'fix bug'. No PR or ticket is linked, so the original motivation isn't recoverable from history."*

### Narrative shape

- **First paragraph:** who wrote this, when, and what the most informative referenced PR / ticket says about why
- **Second paragraph:** how the code has evolved since — follow-up commits, related changes, what *hasn't* changed (signaling load-bearing assumptions)

Keep it tight — the user wants a comment they can paste, not an essay.

### When `gh` is unavailable

The bundle will include a note that `gh` wasn't found and PR bodies are unavailable. In that case:

- Work from commit messages and referenced PR numbers only
- Recommend installing `gh` at the end of the narrative if PR numbers were referenced but couldn't be fetched: *"Install the `gh` CLI for PR descriptions next time — three PR refs (#847, #891, #903) were referenced in commits but their bodies weren't fetched."*

### Never

- Never claim performance impact, customer impact, or business intent without a citation that says so
- Never speculate about what the engineer was "thinking"
- Never invent ticket IDs or PR numbers — only repeat the ones in the bundle
