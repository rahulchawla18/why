# why v1.0.0

First stable release of **why**, a Claude Code plugin that answers *"why is this here?"* for any file, line, or range — grounded in real git history and PR data.

## Highlights

- **`/why <file>[:<line>|:<start>-<end>]`** slash command — pick a file, a single line, or a range and get a 2-paragraph narrative explaining why the code exists.
- **Grounded by construction.** Every factual claim is anchored to a real commit hash, PR number, or file path. If the history doesn't support a claim, the plugin doesn't make it.
- **Runs locally.** No backend, no upload — your repo never leaves your machine. No separate API key, no separate billing.
- **GitHub-aware.** With the `gh` CLI installed, the plugin pulls PR titles, bodies, and linked issues for richer narratives. Without `gh`, it falls back gracefully to commit messages.
- **Distributed as a Claude Code plugin marketplace** — install with a single command, no manual file copying.

## Install

```sh
claude plugin marketplace add rahulchawla18/why
claude plugin install why@why
```

Requirements:

- `git` ≥ 2.20
- Python ≥ 3.10
- `gh` CLI (optional, recommended) — `gh auth login` after install

See [plugin-setup.md](./plugin-setup.md) for the full setup walkthrough.

## What's in the box

| Component | Purpose |
|---|---|
| `/why` slash command | Entry point — invoked inside any Claude Code session |
| `why.cli` Python module | Gathers commits, PRs, and linked refs into a structured Markdown bundle |
| `git_collector` / `gh_collector` | Local git + GitHub data layers, with graceful fallback when `gh` is absent |
| `linked_refs` | Extracts `#N`, `JIRA-456`, `SUPPORT-1234`-style references from commit bodies and PR descriptions |
| Grounding rules baked into the command | Forces citations for every claim; refuses to invent context |

## Known limitations

- **GitHub-only** for rich PR data. Other forges (GitLab, Bitbucket) fall back to commit messages.
- **`<file>:<line>` scope only.** Symbol-level resolution (`/why validateSession`) is planned for a future release.
- **No caching.** Each call re-runs git — fast enough for files with under ~100 commits.
- **No depth limit.** Very long histories pass everything to the model.

## Thanks

Thanks to everyone who tried the early `0.1.0` build and reported the rough edges around plugin packaging, Windows path handling, and the `gh`-unavailable fallback. v1.0.0 is what shipped after those fixes settled.

## License

MIT.
