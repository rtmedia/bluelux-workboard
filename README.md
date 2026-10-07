# Workboard

A local dashboard across Codex chats, Git repositories, worktrees, stashes, and GitHub pull requests. No npm/pip packages or cloud deployment.

## Open it

Double-click **Launch Workboard.command** in Finder, or run `python3 launch.py` from this folder. Open http://127.0.0.1:43127. The launcher reuses an existing Workboard server and otherwise starts one in the background. The launcher reuses the managed server; automatic startup is configured separately.

For a foreground server that stops with Ctrl-C, run `python3 server.py`. Port 43127 is the default; `--port` changes it for a foreground run. The background launcher uses 43127.

## Use it

- Select a project, or keep All projects selected.
- Overview highlights checkouts with local edits and recent conversations.
- Conversations supports title/context/branch search and an archived-chat toggle. Click a card for the recent request, saved response, observed command folders, related checkouts, and **Open in Codex**.
- Workspaces shows every discovered registered checkout, its real branch, file changes, shared chats, cached upstream comparison, and repository stashes.
- **Check GitHub** reads current default-branch and pull-request data through the existing `gh` login. It does not fetch or change local branches.
- The browser refreshes local status every 30 seconds while visible. Refresh is also available manually.

## Status meanings

- **Blue / Recent:** conversation activity during the last seven days.
- **Amber / Needs review:** local file changes. Shared folders mean those changes may belong to another chat.
- **Green / Clean checkout:** no pending non-ignored file changes. This is not proof of a completed task, merged branch, or safe deletion.
- **Gray / Earlier or Unknown:** older activity or missing evidence.
- **Red / Unavailable or Conflict:** failed source read or a Git conflict.

A finished Codex turn means a reply ended, not that the project is complete. Prior response excerpts are historical statements, not newly verified deployment or PR status.

## Sources and limitations

Local projects and chat names are read from Codex's SQLite index with `mode=ro` and `query_only`. Recent user/assistant messages and command working directories are read from bounded tails of saved conversation logs; reasoning, tool output, and credentials files are not extracted. History windows expand from 1 MiB up to 8 MiB when needed. Full history remains in Codex.

This is a version-checked compatibility adapter for the installed Codex data format, not a supported public desktop API. The official app-server protocol was investigated; the desktop control socket is not exposed on this installation. The dashboard does not start a second agent server just to read history. Future Codex schema changes may require an adapter update. Missing history is shown explicitly. This version covers local Codex chats, including locally saved handoffs; cloud-only and ordinary ChatGPT chats are not part of its coverage.

Git origins group worktrees and separately discovered clones of the same GitHub repo. Project membership can span repositories when recent command evidence supports it. One chat can use multiple folders and one folder can serve multiple chats. Branch state is read from Git, not stale chat metadata. Repositories never referenced by local Codex projects or chats are not scanned automatically. Ahead/behind numbers compare cached upstream refs; ignored files are excluded. An untracked directory is counted as one entry. GitHub results are loaded on demand and cached for 60 seconds; errors are not shown as zero PRs.

The server binds only to 127.0.0.1, validates Host and Origin, disables cross-origin reads, serves only explicit assets/routes, and renders untrusted text escaped. It never edits source repositories or Codex data, sends chat messages, merges, deploys, or removes files. No analytics, remote assets, external AI requests, or cloud synchronization are used.

## Verification

`python3 -m unittest -v test_server.py`

`node --check static/app.js`

`python3 server.py --check` runs a local scan and prints counts.

Python 3.10+ and Git are required. The existing GitHub CLI is optional for GitHub checks. All are already available on the Mac used to build this version.

## Focused roadmaps

Workboard opens on **Example Project, Example Site, Example Service, Example Importer, Example Device and Workboard**. Other discovered projects are behind **Other projects**. Sidebar counts represent open recorded task items, not chat totals.

- **Workboard:** core project summaries with a few open items, the latest discussion, and four recent/relevant activity rows.
- **Roadmap:** open, in-progress, next, done and deferred filters. Click a task to read its remaining checklist, source location, directly matching task-ID conversations, and chats linked to the source checkout.
- **Library:** agent instructions, design/architecture documents, plans, task files, configuration and reference files. Filter by category, search inside file contents, and browse readable sections with source paths and versions.
- **Activity:** three most recent discussions plus up to three explicit open-task matches; search to find older conversations (up to 50 results).
- **Workspaces:** the existing checkout inventory, scoped to the selected projects.

The adapter reads up to 120 relevant Markdown/configuration files per known checkout, at most 2 MB per file, excluding generated/ignored/archive folders. It groups identical document copies and deduplicates repeated task IDs. Explicit task status wins over checklist progress; a shipped release can still have unfinished verification. Supporting plan checklists remain within those documents instead of inflating the main TASKS count. Unstructured narrative is shown as reference content, not invented task status.

The default task file is the version with the **newest local Git commit for that file**. This is a transparent selection rule, not proof that the file is canonical, current on GitHub, or fully reconciled. Source branch, date and local edits are shown; choose another TASKS version from the Roadmap selector. That selection persists through refresh in the open page. Recent conversations provide context but never silently mark tasks complete. Cloud-only plans, arbitrary external folders, and plans never saved to matching local Markdown files are not covered.

New source module: `roadmaps.py`. Verification: `python3 -m unittest -q` and `node --check static/app.js`.

## File locations, definitions and version review

Core projects also include **Example Importer** and **Example Device**. Workspaces show full folder paths and **Show in Finder**. The Finder action accepts only a known indexed checkout path, via a same-origin JSON request; it opens Finder without modifying project files.

Hover, focus, or tap view names and status labels for definitions. Multiple distinct task-file contents get an amber warning on the overview and roadmap. **Review versions** lists branches, paths, open/completed item counts, differing recorded statuses, local tracking state, and a source selector. Identical copies are grouped; older distinct contents do not automatically mean unresolved merge conflicts.

**Check task files on GitHub** compares exact file blobs with the current default branch and checks matching file commits on GitHub. Labels distinguish an exact default-branch match, availability in a GitHub commit (possibly historical), and an unverified copy. Local edits are explicitly labelled and a local commit date never implies a push. Checks are read-only, on request, timestamped, and cached for 60 seconds. No files are committed, pushed, merged or deleted by Workboard.


## Permanent home and recovery

Keep the application in a stable local folder so launcher and service paths continue to resolve.

The launcher starts a detached background process. Closing the browser or Codex does not control that process. The site is unavailable while the Mac is asleep or off. **Automatic login startup and restart on exit are enabled** through the user-level macOS launchd service `com.bluelux.workboard`. `Launch Workboard.command` remains a manual fallback and reuses that service. Concurrent launch attempts are locked to prevent duplicate starts.

Click **Service health** in the sidebar, double-click `Check Workboard.command`, or run `python3 check_health.py`. `/api/health` checks the running service independently of source access; `/api/ready` returns 503 until a scan is ready or when degraded. The first scan can take tens of seconds; cached refreshes are faster. A scan exceeding two minutes is reported as degraded. These checks report problems; macOS launchd restarts the server if it exits. A hung but still-running process is reported as degraded and is not automatically killed.

Operational logs are in `.runtime/service.log`, limited to 1 MiB per file with three rotated backups. `.runtime/startup.log` is replaced at each launch. The local move verification receipt is `.runtime/move-receipt.json`.

The Library uses an explicit configuration allowlist, including package manifests, build/lint settings, Docker and deployment files, and GitHub workflows. Markdown instructions, design documents, README files and `tasks/lessons.md` are included. Environment/credential files, lockfiles, dependency folders and generated output are excluded. Files are capped at 2 MiB and 120 candidates per checkout; any discovery limit appears as a warning. Content is displayed as escaped text and is never executed. Full-text search returns at most 60 indexed version matches.

Source is saved in a local Git repository. A private GitHub backup at `rtmedia/bluelux-workboard` is prepared but awaits explicit upload approval. Runtime snapshots, chat/project data, logs, local settings and screenshots are excluded from Git. Future edits need an explicit commit and push to update this backup; Workboard never commits source projects automatically. Check the current backup state with `git status` and `git log -1` in this folder.


## Installed desktop app

Workboard is installable as a PWA at http://127.0.0.1:43127/. Use the **Install app** button in Chrome, or Safari's File → Add to Dock. The installed app opens a separate window. On this Mac the preferred app is the Safari web app at `~/Applications/Workboard.app`, installed with Safari → File → Add to Dock. The Desktop shortcut at `~/Desktop/Workboard.app` points to this Safari version. The earlier Chrome installation remains at `~/Applications/Chrome Apps.localized/Workboard.app`; it is no longer the desktop shortcut target.

Keep the window open and use the app icon to return to it. The browser still needs the local Python server. The local server now starts at login and restarts automatically if it exits. The existing Launch Workboard.command remains a fallback. The app window can stay open independently of Codex; opening the desktop shortcut brings it back.

If the server is stopped when the app opens or reloads, a recovery page appears and retries every five seconds. Only that recovery page and its presentation assets are cached; API responses and project/chat contents are not cached in the browser. Changing the port changes the app's origin, so keep 43127 for the installed app.

PWA verification: `node test_pwa.cjs`.


### Background service controls

The per-user service is saved at `~/Library/LaunchAgents/com.bluelux.workboard.plist`. It runs the existing Python installation, binds only to 127.0.0.1:43127, and keeps the existing bounded service logs. It does not prevent sleep or require administrator privileges.

From this folder, run `python3 service.py status` to check supervision, `python3 service.py disable` to stop it and disable future login startup, or `python3 service.py enable` to re-enable it. Disabling preserves the plist as a `.disabled` file. The service controls the background server; it does not reopen an intentionally closed app window.


## Finish-first workflow

The home view puts discussions with unfinished-work evidence in **Resume**, and lets you choose one **Focus now** discussion. Add a next-step note before leaving for the day. **Needs a decision** contains ambiguous or conflicting evidence; review once and choose Keep open, Mark complete, or Park. **Recently completed** shows completion reports or your closeout choices from the last 30 days. Activity includes older completed discussions. Roadmaps and backlog remain available below the queue and in Roadmap.

Suggestions use saved user/assistant message timestamps, interruptions, explicit follow-up language and exact task-ID matches. They do not infer completion from a finished turn, clean checkout or commit/push alone. “Completion reported” is a conversation signal, not independently verified deployment or GitHub status. Source tasks stay separate and must be reconciled in their actual TASKS.md. Multiple project badges indicate the chat's assigned and observed project folders, not exclusive ownership.

Your choices and notes are atomically saved in `.runtime/triage.json`, excluded from Git and shared by Safari and other local browsers. The service never changes Codex history or source repositories. New requests invalidate older choices; previously completed/parked discussions return for review. “Use suggestion” removes the local override. Missing/corrupt metadata is surfaced instead of silently overwriting it. This file is persistent local user data, not a disposable cache.

Verification: `node test_focus.cjs`, `python3 -m unittest -q`, `node --check static/app.js`, `node test_pwa.cjs`.
