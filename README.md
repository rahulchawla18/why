# Why

> A small Claude Code plugin that answers the question every engineer asks at least once a week: *"why is this here?"*

Pick any file, function, or weird-looking line. Run `/why`. The plugin walks the git history of that exact span, pulls the PR descriptions and linked issues, and writes you a 2-paragraph narrative — the bug it fixed, the conversation that produced it, the engineer who wrote it and when.

It runs **locally** — no backend, no upload, your repo stays your repo. It **refuses to invent**: every claim is anchored to a real commit hash, PR number, or file path. If the history doesn't support a claim, the plugin doesn't make it.

Most code archaeology takes 30 minutes of `git log -L` and tab-switching between PRs. `/why` does it in 5 seconds and writes it as something you can paste into a code comment.

## Install

```sh
claude plugin install rahulchawla18/why
```

You'll also need:

- **`git`** (≥ 2.20) — the plugin shells out to it
- **Python** (≥ 3.10) — for the data-gathering layer
- **`gh`** CLI *(optional, recommended)* — for PR descriptions and linked issues. Install: <https://cli.github.com>. After install, run `gh auth login`. Without `gh`, the plugin still works using commit messages only.

## Usage

```sh
# Whole file
/why src/auth/session.ts

# A single line
/why src/auth/session.ts:42

# A line range
/why src/auth/session.ts:40-55
```

### What the output looks like

```
> /why src/auth/session.ts:42

This line was added in 2023 by Alice in commit a1b2c3d (PR #847,
"Fix stale session race"). The PR description mentions a customer
escalation: sessions were being reused across logins because the
cache key didn't include the auth provider. The unusual `await sleep(50)`
exists as a workaround for a known upstream race in the SSO provider —
see the linked ticket SUPPORT-1234.

Two follow-up commits (#891, #903) modified the surrounding code but
left this line untouched, suggesting the workaround is still load-bearing.
```

Every claim in that narrative is backed by a real commit hash, PR number, or ticket ID gathered from your local git data. If the plugin can't find supporting evidence, it says so plainly instead of guessing.

## How it works

1. The `/why` slash command runs a small Python script that gathers data from your local git repo (and from `gh` if installed).
2. The script prints a structured Markdown bundle to stdout: code in question, commits that touched it, PR titles and descriptions, linked issues.
3. The in-session Claude reads that bundle and writes the narrative, following a grounding rule baked into the slash command: **cite a real commit hash, PR number, or file path for every factual claim**.

No separate API key. No separate billing. No upload of your code anywhere.

## Limitations (v0.1)

- **GitHub-only** for PR data. Works on every repo (commit-message fallback), but the richer narratives need `gh` + a GitHub origin.
- **`<file>:<line>` scope only.** Symbol resolution (`/why validateSession`) is planned for v0.2.
- **No caching.** Each call re-runs git. Fast enough for files with <100 commits.
- **No depth limit.** Very long histories pass everything to the model.

## Develop

```sh
git clone https://github.com/rahulchawla18/why
cd why
python -m venv .venv && source .venv/bin/activate    # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

To try the plugin locally against this repo:

```sh
python -m why.cli README.md
```

## License

MIT.
