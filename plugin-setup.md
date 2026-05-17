# Plugin Setup

How to install the `why` Claude Code plugin on your own machine.

The plugin has two parts:

1. **The slash command** (`/why`) — distributed through this repo's Claude Code marketplace.
2. **The Python data-gathering layer** (`why.cli`) — installed from this repo's `pyproject.toml`. The slash command shells out to `python -m why.cli`, so without it the plugin can't run.

You need both. The sections below cover each.

---

## 1. Prerequisites

| Tool | Version | Required? | Why |
| --- | --- | --- | --- |
| [Claude Code](https://claude.com/claude-code) | latest | yes | runs the slash command |
| `git` | ≥ 2.20 | yes | the script reads git history |
| Python | ≥ 3.10 | yes | runs `why.cli` |
| [`gh` CLI](https://cli.github.com) | latest | optional | fetches PR descriptions and linked issues. Without it, you get commit-message-only narratives. |

After installing `gh`, authenticate once:

```sh
gh auth login
```

---

## 2. Install the Python package

The slash command invokes `python -m why.cli`, so the `why` package must be importable from whatever Python Claude Code finds on `PATH`.

### Option A — from the published repo (recommended)

```sh
pip install "git+https://github.com/rahulchawla18/why.git"
```

### Option B — editable install from a local clone (for development)

```sh
git clone https://github.com/rahulchawla18/why.git
cd why
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
pytest    # sanity check
```

Verify the install:

```sh
python -m why.cli --help
```

> **Heads-up on virtualenvs.** Claude Code launches the slash command in your current shell, so it uses whatever `python` is first on `PATH`. If you installed `why` inside a venv, that venv must be **active** in the shell where you run Claude Code — otherwise the slash command will fail with `No module named why`.

---

## 3. Install the plugin in Claude Code

### Option A — directly from GitHub (recommended for most users)

Inside Claude Code, run:

```
/plugin marketplace add rahulchawla18/why
/plugin install why@why
```

The first command registers this repo as a marketplace (it reads `.claude-plugin/marketplace.json` from the repo root). The second installs the `why` plugin from that marketplace.

### Option B — from a local clone (for plugin development)

If you cloned the repo for development:

```
/plugin marketplace add /absolute/path/to/why
/plugin install why@why
```

Point the path at the **repo root** (the directory containing `.claude-plugin/marketplace.json`), not at `./plugin/`.

### Verify

In any Claude Code session, type `/` and confirm `/why` appears in the slash-command list. Then try it on this repo:

```
/why README.md
```

You should get a 2-paragraph narrative grounded in real commits.

---

## 4. Updating

```
/plugin marketplace update why
/plugin update why@why
```

If you also installed the Python package from git, re-run the `pip install "git+https://..."` command to pick up changes in `why.cli`.

---

## 5. Uninstall

```
/plugin uninstall why@why
/plugin marketplace remove why
pip uninstall why-plugin
```

---

## Troubleshooting

**`/why` isn't listed after install.**
Restart Claude Code. If still missing, run `/plugin list` and confirm the marketplace and plugin both appear.

**`No module named why` when running `/why`.**
The Python package isn't on the `PATH` Claude Code sees. Activate the venv where you installed `why` *before* launching Claude Code, or install `why` into your system Python with `pip install --user "git+https://github.com/rahulchawla18/why.git"`.

**`fatal: not a git repository`.**
`/why` only works inside a git working tree. `cd` into one first.

**PR bodies missing from the narrative.**
`gh` isn't installed or isn't authenticated. Run `gh auth status`. The plugin still works without it, but narratives are limited to commit-message content.

**File-not-tracked error.**
The script refuses untracked files — there's no history to read. Commit (or at least `git add`) the file first.
