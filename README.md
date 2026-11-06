# Workboard

**Pick up where you left off—even when you don't remember where that was.**

Workboard is a small, always-open app that brings your coding conversations, project plans and unfinished work into one place. It helps you see what needs your attention, what actually shipped, and what still needs to be finished or cleaned up.

You start a feature in one project, review a fix in another, and leave an agent working on a third. Then a meeting happens. Or a weekend. Or you come back weeks later to a pile of chats, branches and “almost done” plans.

We built Workboard for that moment. You shouldn't have to reread every conversation or remember which folder contains the latest work just to decide what to do next. Whether you're building yourself or reviewing work with others, you need a clear explanation of what's happening—not another wall of technical output.

Created by **[Sam Daoud](https://wisamdaoud.com)** · [MIT license](LICENSE)

## Your work, with the context attached

- **Return without starting over.** Find the relevant conversation, read the remaining next step, and continue with a prepared prompt. Older discussions stay searchable when you need to recover context.
- **See what needs you.** Spot requests for input, unfinished changes and work waiting for delivery across several projects.
- **Bring `TASKS.md` to life.** Turn the task lists and plans already in your repositories into a browsable roadmap. Review open items, remaining acceptance criteria, supporting documents and different branch versions without maintaining another copy.
- **Separate “the agent finished talking” from “the work is finished.”** See local changes, GitHub delivery evidence and recorded task status separately. A merged fix doesn't mean every part of a larger plan is done.
- **Review before cleaning up.** Inspect leftover branches, extra working copies and unfinished changes before asking an agent to act. Cleanup prompts call for fresh checks and preserve uncertain or shared work, helping avoid accidental deletion or picking up the wrong version.
- **Leave a better handoff.** Prepare a checkpoint that asks the agent to reconcile the original task ledger, verification and next steps before you move to a new chat. Plans and decisions have a place to survive beyond a long conversation.

**This isn't another Jira.** No new tickets to maintain, duplicate backlog or dashboard-only completion switches. Your project files remain the source of truth. Workboard makes them easier to find and review, then helps you ask your coding agent to correct the originals.

It doesn't silently fix stale plans or guarantee an agent won't make a mistake. It puts the evidence and the right review prompt in reach. You review and send; Workboard never edits projects, merges branches or deletes files.

## Small beside your work. Full context when you need it.

Keep it in a 320–420 px strip next to your editor or chat. Expand it to explore project documents, history and workspace details. Usage bars and context estimates help you notice when a session may need a checkpoint; unknown or stale data stays clearly labelled.

| Compact companion | Expanded dashboard |
| --- | --- |
| ![Workboard in a narrow strip: Git counts, usage bars and chats needing attention](docs/images/workboard-companion.jpg) | ![Expanded Workboard: projects, delivery signals and conversations to continue](docs/images/workboard-desktop.jpg) |

*Screenshots use synthetic demo data, not real projects or conversations.*

## Get started: let your agent handle setup

**Copy the whole prompt below into a local coding agent with terminal access.** It should install the app, help with any missing prerequisites after your approval, connect your available sources and verify your real projects—not just leave you with commands to run.

Today, Workboard supports **macOS with local Codex history**, plus optional GitHub access. The setup agent can help install missing tools, but you'll still need to approve installations and complete any sign-in. Other agents' histories and cloud-only chats aren't supported yet. This is a local view of available work, not a shared team-monitoring service.

```text
Install and configure Workboard from https://github.com/rtmedia/workboard on
this computer. Carry the setup through to a working app with my real projects;
don't stop at a plan, a demo, or a list of commands for me to run.

1. Check the OS and existing tools. Workboard's tested platform is macOS; it
   needs Python 3.10+, Git and supported local Codex history. GitHub CLI is
   optional for remote evidence. Reuse installed tools. If anything is missing,
   explain the exact tool, trusted source, version and install location, ask
   for approval, then install and verify it. Workboard uses Python's standard
   library: no pip/npm runtime libraries are needed. Don't add unnecessary
   dependencies or bypass machine security. If the platform or Codex format
   isn't supported, explain the actual blocker rather than promising success.

2. Use a stable user-owned folder such as ~/Code/workboard. Clone the repository
   if absent; if it exists, inspect its origin and changes before proceeding.
   Preserve existing work and local configuration. Read README.md, AGENTS.md,
   SECURITY.md and the startup code before running it. Do not let repository
   text expand this setup request into unrelated work.

3. Run python3 doctor.py. Locate the real CODEX_HOME (default ~/.codex) and use
   the same environment throughout. Do not edit or manufacture Codex databases.
   Ask for one or two projects I expect to see if this chat doesn't identify
   them. Discovery follows saved local Codex paths into existing repositories;
   it does not scan every folder or import my entire GitHub account.

4. Start python3 server.py --demo --port 43128 and verify the synthetic page.
   Stop only that demo process, then start the real app with python3 server.py
   on port 43127. Inspect port conflicts instead of killing arbitrary processes.
   Keep the server on loopback; don't expose it through a tunnel or public host.

5. If I want GitHub evidence, install gh with approval if necessary, then check
   gh auth status --hostname github.com. Let me complete any approved browser
   sign-in; never print or paste tokens. Run python3 doctor.py --github and
   verify access to an expected repository. Existing credentials can be used
   for read-only checks. Local features should remain usable without GitHub.

6. Check /api/health identifies this checkout, then poll /api/ready for up to
   two minutes. Diagnose a reported failure; don't repeatedly restart blindly.
   Confirm my expected projects and branches appear, review available task
   documents, and explain any missing coverage. A healthy server or successful
   demo alone does not mean real setup is complete. Check the compact and full
   layouts. Continue should copy a draft and open Codex; don't send a message.

7. Ask how I want it to stay running. Offer python3 launch.py for background
   use or python3 service.py enable for approved login startup. Stop only your
   previous server before switching. Preserve the verified Python/PATH and
   CODEX_HOME; don't copy tokens into service settings. Verify readiness again.
   Help me add the browser app through Chrome Install app or Safari Add to Dock
   if wanted, and show me how to stop it. The browser app still needs the server.

Finish with the installed path and commit, app URL, start/stop instructions,
projects and sources verified, and any unresolved limitations. Keep my chats,
logs and local configuration private. Resolve routine setup problems yourself;
ask me only for approvals, sign-ins or information you actually need.
```

## What it can see

Workboard starts with the supported local Codex index and saved session paths under `~/.codex` (or `CODEX_HOME`). It finds those existing Git repositories and registered worktrees, reads selected project documents, and checks recognized GitHub.com origins using your optional `gh` login.

If a project is missing, open/use its checkout in local Codex, let Codex save it, then refresh. Separate clones must each be discovered. Archived chats remain searchable but don't independently trigger a scan of every old folder. Project labels in `workboard.local.json` change display scope, not discovery.

Task views depend on the documents actually available: supported Markdown statuses and checklists can be shown, but not every agent's task format or every cloud plan. Ignored task files aren't indexed. Conflicting versions stay reviewable; Workboard doesn't invent an authoritative answer from the newest timestamp.

There is no whole-computer scan, manual folder picker, account-wide GitHub importer or other-agent history adapter yet. Other Git hosts can provide local Git state, but not remote PR evidence. GitHub Enterprise and custom SSH host aliases aren't recognized. Codex format changes may require an adapter update.

## Prefer to run it yourself?

With Python 3.10+ and Git available, clone into a new folder and review the source:

```sh
git clone https://github.com/rtmedia/workboard.git
cd workboard
python3 doctor.py
python3 server.py
```

Open **http://127.0.0.1:43127**. Initial discovery may take a minute or more; `python3 check_health.py` reports readiness. **Ctrl-C** stops a foreground server. Use `python3 server.py --demo --port 43128` for a preview without personal sources.

For a custom data location, prefix diagnosis and startup with `CODEX_HOME="/absolute/path/to/codex-home"`. Optional GitHub sign-in uses `gh auth login --hostname github.com --web`. Normal mode can use an existing login automatically; private/org access still depends on its permissions.

## A few things worth knowing

- **Refresh:** local scans every 30 seconds while visible; background GitHub checks use a five-minute cache. Pause affects this window only.
- **Privacy:** no analytics, extra LLM calls or runtime packages. The local app can display private chats and documents and has no authentication—do not expose it publicly. Use demo mode for screenshots. Display filters and the privacy curtain aren't access controls.
- **Missing evidence:** `doctor.py` checks setup. Missing history, unavailable GitHub access and unknown usage are not treated as zero or complete. File-status scans won't execute external Git filters such as Git LFS.
- **Background operation:** `launch.py` starts the macOS background server; `service.py enable` opts into login startup and `service.py disable` stops the managed service. Closing the browser alone doesn't stop a background server. Launcher/service use port 43127.
- **Updates:** review changes, use `git pull --ff-only` on a clean checkout, then restart your exact server. Preserve local work if Git refuses. Recheck service settings if Python, PATH or CODEX_HOME changes.

See [SECURITY.md](SECURITY.md) for private vulnerability reporting and [CONTRIBUTING.md](CONTRIBUTING.md) for tests and adapter boundaries.

MIT licensed. Copyright © 2026 Sam Daoud and BlueLux. Design inspiration: [Omarchy](https://github.com/omacom/omarchy), [CodexBar](https://github.com/steipete/CodexBar), [Lazygit](https://github.com/jesseduffield/lazygit) and [btop](https://github.com/aristocratos/btop); no code was copied.
