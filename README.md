# Workboard

Product intent is defined in [CHARTER.md](CHARTER.md). The [source-of-truth plan](TASKS.md#wb-source-truth--view-only-workboard-and-source-reconciliation--done) replaces manual tracking with contextual Codex prompt handoffs, including Reconcile. The view-only controls and prompt handoffs are now implemented.

A local dashboard across Codex chats, Git repositories, worktrees, stashes, and GitHub pull requests. No npm/pip packages or cloud deployment.

## Open it

Double-click **Launch Workboard.command** in Finder, or run `python3 launch.py` from this folder. Open http://127.0.0.1:43127. The launcher reuses an existing Workboard server and otherwise starts one in the background. The launcher reuses the managed server; automatic startup is configured separately.

For a foreground server that stops with Ctrl-C, run `python3 server.py`. Port 43127 is the default; `--port` changes it for a foreground run. The background launcher uses 43127.

## Use it

- Select a project, or keep All projects selected.
- Overview prioritizes unfinished work, remaining delivery, project follow-up and verified recent completion.
- History supports title/context/branch search and an archived-chat toggle. Click a card for the recent request, saved response, observed command folders, related checkouts, and **Open in Codex**.
- Workspaces shows every discovered registered checkout, its current branch, file changes, historical chat associations, recommended next step, cached upstream comparison, and repository stashes.
- **Check GitHub** reads current default-branch and pull-request data through the existing `gh` login. It does not fetch or change local branches.
- The browser refreshes local status every 30 seconds while visible. Refresh is also available manually.

## Status meanings

- **Blue / Recent:** conversation activity during the last seven days.
- **Amber / Local changes:** changed or untracked files. Shared folders mean those changes may belong to another chat.
- **Gray / No file changes:** no pending non-ignored file changes. This is not proof of a completed task, merged branch, or safe deletion.
- **Gray / Earlier or Unknown:** older activity or missing evidence.
- **Red / Unavailable or Conflict:** failed source read or a Git conflict.

A finished Codex turn means a reply ended, not that the project is complete. Prior response excerpts are historical statements, not newly verified deployment or PR status.

## Sources and limitations

Local projects and chat names are read from Codex's SQLite index with `mode=ro` and `query_only`. Recent user/assistant messages and command working directories are read from bounded tails of saved conversation logs; reasoning, tool output, and credentials files are not extracted. History windows expand from 1 MiB up to 8 MiB when needed. Full history remains in Codex.

This is a version-checked compatibility adapter for the installed Codex data format, not a supported public desktop API. The official app-server protocol was investigated; the desktop control socket is not exposed on this installation. The dashboard does not start a second agent server just to read history. Future Codex schema changes may require an adapter update. Missing history is shown explicitly. This version covers local Codex chats, including locally saved handoffs; cloud-only and ordinary ChatGPT chats are not part of its coverage.

Git origins group worktrees and separately discovered clones of the same GitHub repo. Project membership can span repositories when recent command evidence supports it. One chat can use multiple folders and one folder can serve multiple chats. Branch state is read from Git, not stale chat metadata. Repositories never referenced by local Codex projects or chats are not scanned automatically. Ahead/behind numbers compare cached upstream refs; changed-file counts exclude ignored files, which are inventoried separately as cleanup blockers. An untracked directory is counted as one entry. Detailed GitHub checks are loaded on demand and cached for 60 seconds; background delivery checks use a five-minute cache. Errors are not shown as zero PRs.

The server binds only to 127.0.0.1, validates Host and Origin, disables cross-origin reads, serves only explicit assets/routes, and renders untrusted text escaped. It never edits source repositories or Codex data, sends chat messages, merges, deploys, or removes files. No analytics, remote assets, external AI requests, or cloud synchronization are used.

## Verification

`python3 -m unittest -v test_server.py`

`node --check static/app.js`

`python3 server.py --check` runs a local scan and prints counts.

Python 3.10+ and Git are required. The existing GitHub CLI is optional for GitHub checks. All are already available on the Mac used to build this version.

## Focused roadmaps

Workboard opens on **Example Project, Example Site, Example Service, Example Importer, Example Device and Workboard**. Other discovered projects are behind **Other projects**. Sidebar counts represent open recorded task items, not chat totals.

- **Workboard:** one action queue. Click the Resume, Cleanup, In progress or Recently completed dashboard card to filter it; Overview restores the combined view. Reconcile / verify prioritizes task-linked contradictions and recent uncertain discussions. Older unlinked uncertainty stays in History. Filters are temporary views, not saved task statuses.
- **Roadmap:** open, in-progress, next, done and deferred filters. Click a task to read its remaining checklist, source location, directly matching task-ID conversations, and chats linked to the source checkout.
- **Library:** agent instructions, design/architecture documents, plans, task files, configuration and reference files. Filter by category, search inside file contents, and browse readable sections with source paths and versions.
- **History:** indexed discussions in date order, with search and an archived-chat toggle. It is for retrieving past context, without repeating the action queue.
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

Source is saved in a local Git repository. The user approved a private GitHub source repository at `rtmedia/bluelux-workboard`; publication is recorded in TASKS.md. Runtime snapshots, chat/project data, logs, local settings and screenshots are excluded from Git. Future edits need an explicit commit and push to update this backup; Workboard never commits source projects automatically. Check the current backup state with `git status` and `git log -1` in this folder.


## Installed desktop app

Workboard is installable as a PWA at http://127.0.0.1:43127/. Use the **Install app** button in Chrome, or Safari's File → Add to Dock. The installed app opens a separate window. On this Mac the preferred app is the Safari web app at `~/Applications/Workboard.app`, installed with Safari → File → Add to Dock. The Desktop shortcut at `~/Desktop/Workboard.app` points to this Safari version. The earlier Chrome installation remains at `~/Applications/Chrome Apps.localized/Workboard.app`; it is no longer the desktop shortcut target.

Keep the window open and use the app icon to return to it. The browser still needs the local Python server. The local server now starts at login and restarts automatically if it exits. The existing Launch Workboard.command remains a fallback. The app window can stay open independently of Codex; opening the desktop shortcut brings it back.

If the server is stopped when the app opens or reloads, a recovery page appears and retries every five seconds. Only that recovery page and its presentation assets are cached; API responses and project/chat contents are not cached in the browser. Changing the port changes the app's origin, so keep 43127 for the installed app.

PWA verification: `node test_pwa.cjs`.


### Background service controls

The per-user service is saved at `~/Library/LaunchAgents/com.bluelux.workboard.plist`. It runs the existing Python installation, binds only to 127.0.0.1:43127, and keeps the existing bounded service logs. It does not prevent sleep or require administrator privileges.

From this folder, run `python3 service.py status` to check supervision, `python3 service.py disable` to stop it and disable future login startup, or `python3 service.py enable` to re-enable it. Disabling preserves the plist as a `.disabled` file. The service controls the background server; it does not reopen an intentionally closed app window.


## Finish-first workflow

The home view prioritizes **Resume**, **Finish delivery**, **Project follow-up**, **Recently completed** and **Evidence unclear**. Classification comes from recorded source evidence; there are no saved focus, completion/parking overrides or next-step notes, and the old triage write API rejects requests. Workboard is a reader, not a second task ledger.

A contextual **Continue**, **Finish delivery** or **Reconcile status** button copies a scoped prompt and opens the exact chat. **Reconcile project** in Roadmap and Library prepares an artifact-review prompt and lists project-associated chats for the user to choose. Workboard does not choose ownership from recency and never submits the prompt. Read-only prompt previews and manual-copy fallbacks remain available.

The latest request, interruptions, remaining steps and exact task-ID links inform the queue. Cited commits/PRs are independently checked against the default branch. A later unfinished work unit can keep a conversation in Resume; earlier delivery evidence stays in its details, without a competing completion badge. Source task status must be corrected in the project, not overridden here. Unknown local-only/cloud-only completion stays explicit.

Verification: `node test_focus.cjs`, `python3 -m unittest -q`, `node --check static/app.js`, `node test_pwa.cjs`.

## Git-backed delivery and Cleanup

The delivery milestone is a work unit's explicit PR or labelled commit appearing on the current GitHub default branch (main in the core projects). GitHub is read through the existing `gh` sign-in; no fetch, checkout, branch deletion or source-repository writes occur. Background checks are separate from local inventory/health, use a five-minute remote cache, publish repository results as they finish, and bound each repository check to roughly 90 seconds plus an outstanding request. **Check delivery now** bypasses the remote cache. Coverage limits and unavailable evidence are displayed.

**Resume** contains unfinished execution/delivery. Local changes and unfinished branches that may span chats appear under **Preserve / reconcile** in Overview and Reconcile / verify. **In progress** counts started source tasks/plans needing follow-up. **Recently completed** contains cited work verified on the default branch. A newer request reopens a discussion; sharing a clean/main checkout never completes every linked chat. **Evidence unclear** is kept separate from concrete cleanup obligations.

**Cleanup** lists delivered branches and extra worktrees separately from completion. A completed item can display **On main · Cleanup pending**. Exact PR-head matching plus merge-commit ancestry handles squash/rebase merges; newer commits on a branch remain protected. Local and remote leftovers are distinguished. Default/protected branches and primary checkouts are retained. Changed, untracked, ignored, locked and otherwise unverified work is flagged for inspection. No deletion button exists: an actual cleanup requires a separate exact-target inspection and approval under the local deletion policy. Repository stashes are counted separately.

Deployment is independent of the main-branch completion milestone. Explicit Render statuses/check runs on the current default-branch tip are shown when GitHub exposes them; otherwise deployment is **not checked**, not assumed successful. Failed/pending Render checks appear as follow-up notices without relabelling delivered code as unfinished.

Additional verification: `python3 -m unittest -q`, `node test_focus.cjs`, `node test_delivery_ui.cjs`.

### Session cleanup prompts
Delivered discussions with verified leftovers have **Clean up session ↗** as their single contextual action. It copies a prompt limited to that chat and opens its existing Codex chat; paste and send there. Open discussion details to preview the prompt first. If clipboard access is unavailable, the draft remains selectable in Workboard. No cleanup command is sent or executed by Workboard.

The prompt requires fresh delivery and ownership evidence, leaves uncertain work in place, asks for concrete decisions, prohibits creating stashes/backups as a workaround, and preserves chat history. A completed session may remove its verified disposable worktree without a replacement checkout; Workboard retains the chat through saved repository identity and shows a neutral “No local checkout” label. Folder absence alone does not establish completion. Project/workspace associations are leads, not ownership proof. Tool-created recovery snapshots also need an explicit decision.


## Instructions and lightweight workflow

Open **Instructions** to read the current local global AGENTS.md, any AGENTS.override.md, the Workboard charter, and indexed project instruction versions. Paths, source modification times, read errors and local coverage limits are visible. Global sources are read fresh from an exact allowlist through GET /api/instructions; there is no instruction-save API or arbitrary file-path parameter. Symlinks, non-regular files and sources larger than 64 KiB are rejected. Codex configuration, credentials and local permission settings are not exposed by this endpoint.

**Request an instruction change** provides a preview and a copyable prompt. Add the behavior you want changed in Codex. **Copy & open** links target the chosen existing Workboard-associated chat; the association is context, not ownership. No chat is selected automatically and nothing is submitted. Safari's selection-copy fallback is supported. Reload instructions or Refresh to read subsequent source edits.

Project guidance maps the local task ledger and supporting artifacts. Global machine instructions are not automatically available in other environments.

Library Configuration means build/test/runtime infrastructure, not disposable clutter. Product playbook documents are categorized by role rather than mistaken for agent instructions. Remaining CLAUDE.md copies are labeled legacy guidance; review their source checkout. Historical plans and reports require task-by-task reconciliation before retirement. Personal-tracking removal has been completed; Continue and Reconcile are implemented as prompt handoffs.


### When the framework takes effect

Instructions → Global Codex instructions → Development working agreement shows the lightweight framework read from `~/.codex/AGENTS.md`. Request an instruction change prepares a Codex prompt; Workboard has no settings editor or instruction-save API.

Codex builds its instruction chain at the start of a run. This Workboard chat was verified to contain the new agreement in its loaded instructions on October 6, 2026. No application restart is needed for this chat to use it. In an older chat, ask Codex to read the current global and project AGENTS.md before continuing; if automatic instructions look stale, start a fresh session/run in the intended project. Restarting does not update files in old checkouts or copy this Mac's global instructions into cloud environments. See [official instruction discovery guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Verification limits: Safari prompt copying, source refresh and removed-worktree continuity have been exercised. Exact Codex links and failure fallbacks are tested, but native foreground navigation into Codex could not be visually confirmed. Instructions displays files available locally, not proof of every chat's effective instruction stack. Cloud-only chats are not covered by the local reader.


## Focused queue and checkout review

Cleanup is a Workboard filter, not a separate tab. In progress lists started/blocked source tasks; Recently completed lists discussions with delivery evidence from the last 30 days. Roadmap retains the full project backlog, Library the documents, Instructions the guidance, and Workspaces the exact local folders. Dashboard counts follow the selected project and search; Git groups and task records remain distinct from discussion counts.

Chat details have one status/action panel, a collapsed evidence section, and the request/response context. Click outside the flyout, press Escape, or use its close button to dismiss it. Clean up session copies the prompt during the click and requests navigation to the exact `codex://threads/...` link. Paste with Command-V and send in Codex; auto-paste and auto-send are not performed. A visible prompt and direct link remain if clipboard access or app opening fails. Browser navigation cannot confirm that Codex actually displayed the destination.

In Workspaces, **Review cleanup in Codex** prepares a prompt limited to the exact indexed checkout and its directly associated temporary branch. Choose a linked chat to copy and open it, or copy only when no appropriate chat is listed. Association does not prove ownership. Codex must inspect fresh state, keep primary checkouts/default branches, preserve unfinished/shared/ignored data, and ask about concrete uncertain targets or deletion approval. The dashboard never deletes folders or creates preservation artifacts.


## Evidence-based next actions

The sidebar explicitly labels **open tasks**, with a project-level breakdown of in-progress/blocked and planned items. This is not the number of unfinished chats or checkouts. The banner names the selected task-file branch, file commit date and version count. The default still uses the newest local file commit; it does not silently claim that branch is authoritative.

An exact task-ID match connects an old chat to its selected project task record. If an old handoff says work remains while the record says Done or Deferred, the discussion moves to **Reconcile status**, outside Resume. The detail shows the dated chat, matched records and exact source path. A file commit date is not a task-completion timestamp. New unanswered requests and interrupted turns retain their own priority; mixed scopes remain explicit. Reconciliation verifies later work against code, delivery and original records before restarting anything. It does not automatically mark the chat completed from a checkbox. Task-linked conflicts are prioritized; older unlinked uncertainty remains searchable in History.

Checkout recommendations are independent of chat completion:

- **Keep primary checkout:** retain the shared project home; reconcile unresolved changes in place.
- **Preserve · reconcile work:** changed/untracked files or unique/unverified branch work need investigation before cleanup.
- **Verify delivery · keep for now:** delivery evidence is missing, stale or does not match the checkout tip.
- **Review cleanup:** current matching delivery evidence identifies temporary leftovers; Codex still checks ownership, ignored files, active use and deletion rules.

Chat-folder links describe historical use, not exclusive ownership. The displayed branch is checked out now, not necessarily the branch used by the old chat. Counts of historical chat links are not active-user counts. Recommendation-specific prompts carry the exact folder and evidence into Codex; they never create stashes, backup branches, bundles or another checkout merely to avoid a decision.
