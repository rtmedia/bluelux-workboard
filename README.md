# Workboard

**Keep your projects in view without keeping another task list.**

A small, always-open companion for Codex chats, Git workspaces and GitHub pull requests. See what needs you, pick up unfinished work, and keep an eye on branches and usage without leaving your flow.

Created by **[Sam Daoud](https://wisamdaoud.com)** · [MIT license](LICENSE)

| Compact companion | Expanded dashboard |
| --- | --- |
| ![Workboard in a 390-pixel strip: Git counts, usage bars and chats needing attention](docs/images/workboard-companion.jpg) | ![Workboard expanded: project navigation, Git signals and conversations to continue](docs/images/workboard-desktop.jpg) |

*Screenshots use synthetic demo data, not real projects or conversations.*

## What it does

- Shows unfinished chats, changed files, branches and GitHub delivery evidence.
- Displays context estimates and saved usage/reset signals. Missing or stale data stays explicit.
- Reads original task lists and project documents instead of creating a second task tracker.
- Copies a continuation prompt and opens the matching Codex chat. You paste and send.
- Fits a 320–420 px strip, with a full dashboard when expanded.

No runtime packages, build step, LLM calls or analytics. Workboard does not edit your projects, send messages, merge branches or delete files.

## How it finds your work

**Local Codex paths → Git repositories and registered worktrees → project documents → GitHub origins.**

Workboard reads the supported local Codex index and saved session paths under `~/.codex` (or `CODEX_HOME`). It inspects those existing checkouts and their worktrees, then uses your optional `gh` login to check recognized GitHub.com origins.

It **does not search your whole computer or import every repository in your GitHub account**. If a project is missing, open/use its checkout in local Codex, let Codex save it, then refresh. Separate clones must each be discovered. Archived chats remain searchable but don't independently trigger a scan of all old folders.

This is an **early macOS release for local Codex users**. Other agents, cloud-only chats, GitHub Enterprise and a manual folder picker are not supported yet. Other Git hosts can provide local Git state, but not remote PR evidence. Codex format changes may require an adapter update.

## Get started

You need **Python 3.10+**, **Git**, and local Codex with saved project activity. GitHub CLI is optional. Node is only needed for contributor tests. Install missing tools through a trusted source; Workboard installs nothing itself.

Clone into a new, stable folder you own, then review the source before running:

```sh
git clone https://github.com/rtmedia/workboard.git
cd workboard
python3 doctor.py
python3 server.py
```

Open **http://127.0.0.1:43127**. Keep the terminal open; **Ctrl-C** stops the server. Initial discovery may take a minute or more. In another terminal, `python3 check_health.py` should eventually report `ready`; a running server alone doesn't prove its sources are available.

**Try without personal data:** run `python3 server.py --demo --port 43128` and open **http://127.0.0.1:43128**. Demo mode reads no personal sources.

**GitHub:** with `gh` installed, run `gh auth status --hostname github.com`. If you want to sign in, use `gh auth login --hostname github.com --web`, then `python3 doctor.py --github`. Normal mode can use an existing login automatically. Private/org access still depends on that account's permissions; never paste tokens into Workboard.

**Custom Codex location:** use the same setting for diagnosis and startup:

```sh
CODEX_HOME="/absolute/path/to/codex-home" python3 doctor.py
CODEX_HOME="/absolute/path/to/codex-home" python3 server.py
```

**Keep it open:** `python3 launch.py` starts a background server on macOS. Optional login startup uses `python3 service.py enable`; stop the previous server first. `python3 service.py disable` stops the managed service. Chrome's Install app or Safari's Add to Dock gives it its own window, but still needs the Python server.

## Let your coding agent set it up

Paste this into a local coding agent with terminal access:

```text
Set up Workboard from https://github.com/rtmedia/workboard and verify it with
my real local projects. Read its README.md, AGENTS.md and SECURITY.md first.

Check macOS, Python 3.10+, Git and optional gh. Ask before installing missing
tools, changing a login, or enabling login startup. No pip/npm packages are
needed. Use a stable folder such as ~/Code/workboard; inspect any existing
checkout and preserve its changes rather than overwriting or duplicating it.

Run doctor.py. Locate the real CODEX_HOME (default ~/.codex), and use the same
environment for diagnosis and startup. Do not edit Codex databases. Explain
that discovery follows local Codex paths, not the whole disk/GitHub account.
Ask for one expected project to verify if the context doesn't identify one.

Start server.py --demo --port 43128 first and verify the synthetic page. Stop
only that process, then start server.py on port 43127. Identify port conflicts
instead of killing arbitrary processes. Keep the listener on loopback.

Check /api/health for this checkout and /api/ready for up to two minutes.
Confirm the expected project and branch appear. If GitHub is wanted, check
the existing gh login and one expected repository; let me complete any new
browser login, without printing tokens. Missing sources are not success.

Verify the compact and expanded views. Continue should copy a draft and open
Codex; don't send a message. Offer background/login startup and a browser app
as separate choices. Preserve the selected Python/PATH/CODEX_HOME if enabling
the service, then verify readiness again. Do not copy token variables into it.

Finish with the installed path/commit, URL, how to start/stop, what was verified
and any missing coverage. Don't upload my logs, chats or local configuration.
```

## Useful details

- **Refresh:** local scans every 30 seconds while visible; background GitHub checks use a five-minute cache. Pause affects this window only.
- **Project labels:** copy `workboard.example.json` to ignored `workboard.local.json`. This changes display scope, not discovery roots. Restart after changes.
- **Missing data:** `doctor.py` checks setup; `--json` helps agents. No supported Codex index means demo-only use. Don't repair this by editing the database.
- **GitHub errors:** check the login, repository permissions and `origin` URL. Standard GitHub HTTPS/SSH URLs are supported; custom SSH aliases aren't recognized.
- **Git filters:** file-status scans are unavailable when tracked files require external filters such as Git LFS. Workboard won't execute those helpers.
- **Port conflict:** inspect the existing process or use `server.py --port 43129` with the matching URL. The launcher/service use 43127.
- **Login startup:** records the selected Python, PATH, CODEX_HOME and optional GH_CONFIG_DIR, not shell-only tokens. Already-loaded services need deliberate reconfiguration when these change.
- **Updates:** review changes, use `git pull --ff-only` on a clean checkout, then restart your exact server. Preserve local work if Git refuses.

## Privacy and contributing

Run on a trusted, single-user machine. **Do not expose the server publicly:** it has no authentication and can display private local chats, paths and documents. Filters and the screen-share curtain are not access controls. Use demo mode for screenshots; Git ignore does not stop cloud-folder synchronization.

See [SECURITY.md](SECURITY.md) for the security model and private reporting, and [CONTRIBUTING.md](CONTRIBUTING.md) for tests and adapter boundaries. Manual discovery roots, other-agent adapters and broader platform testing remain future work.

MIT licensed. Copyright © 2026 Sam Daoud and BlueLux. Design inspiration: [Omarchy](https://github.com/omacom/omarchy), [CodexBar](https://github.com/steipete/CodexBar), [Lazygit](https://github.com/jesseduffield/lazygit) and [btop](https://github.com/aristocratos/btop); no code was copied.
