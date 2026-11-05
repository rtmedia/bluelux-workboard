# Workboard

Created by **Wisam Daoud and BlueLux**. Copyright © 2026 Wisam Daoud and BlueLux. Licensed under the [MIT License](LICENSE).

Product intent is defined in [CHARTER.md](CHARTER.md). Workboard provides view-only observations and contextual Codex prompt handoffs. This README covers usage and operations; [AGENTS.md](AGENTS.md) defines project development guidance. The local canonical ledger `TASKS.md` and personal correction notes `tasks/lessons.md` are kept on disk but intentionally excluded from Git. They are not part of a public checkout.

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

## Compact companion

At window widths of 600 px or less, Workboard switches to a companion layout designed for a 320–420 px strip. A sticky header holds project scope, the view selector, refresh and the last local scan time. Recent discussions and delivery steps appear first, followed by expandable project rows. Source evidence, reconciliation, cleanup and recent completions remain available in disclosures. Search filters the current scope; selecting a project or view changes presentation only.

Use **↗ Show full dashboard** to show the full controls in the same window and **↙ Return to companion** to return. Widening past 600 px automatically restores the existing expanded layout. All six views remain accessible through the view selector. Details fill a narrow window, with a sticky close control. Existing chat handoffs still copy a draft and open Codex without sending it.

Companion chat ordering remains stable within each group for the open page; refresh preserves expanded disclosures and scroll position. Source changes can still move an item between groups. A scan older than two minutes is labeled stale; unavailable-server errors remain visible. This is not an always-on-top window manager or an independent task store.

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

`python3 -m unittest -q`

`node test_focus.cjs`, `node test_delivery_ui.cjs`, `node test_cleanup.cjs`, `node test_pwa.cjs`

`node --check static/app.js`

`python3 server.py --check` runs a local scan and prints counts.

Python 3.10+ and Git are required. The existing GitHub CLI is optional for GitHub checks. All are already available on the Mac used to build this version.

## Focused roadmaps

Workboard opens on all discovered projects unless local configuration selects a smaller main scope. Other discovered projects remain behind **Other projects**. Sidebar counts represent open recorded task items, not chat totals.

- **Workboard:** one action queue. Click the Resume, Cleanup, In progress or Recently completed dashboard card to filter it; Overview restores the combined view. Reconcile / verify prioritizes task-linked contradictions and recent uncertain discussions. Older unlinked uncertainty stays in History. Filters are temporary views, not saved task statuses.
- **Roadmap:** open, in-progress, next, done and deferred filters. Click a task to read its remaining checklist, source location, directly matching task-ID conversations, and chats linked to the source checkout.
- **Library:** agent instructions, design/architecture documents, plans, task files, configuration and reference files. Filter by category, search inside file contents, and browse readable sections with source paths and versions.
- **History:** indexed discussions in date order, with search and an archived-chat toggle. It is for retrieving past context, without repeating the action queue.
- **Workspaces:** the existing checkout inventory, scoped to the selected projects.

The adapter reads up to 120 relevant Markdown/configuration files per known checkout, at most 2 MB per file, excluding generated/ignored/archive folders. It groups identical document copies and deduplicates repeated task IDs. Explicit task status wins over checklist progress; a shipped release can still have unfinished verification. Supporting plan checklists remain within those documents instead of inflating the main TASKS count. Unstructured narrative is shown as reference content, not invented task status.

The default task file is the **primary project ledger when available**, with the newest local file commit used only as a fallback. This selection rule is not proof that local content is current on GitHub or fully reconciled. Source branch, date and local edits are shown; choose another TASKS version from the Roadmap selector. That selection persists through refresh in the open page. Recent conversations provide context but never silently mark tasks complete. Cloud-only plans, arbitrary external folders, and plans never saved to matching local Markdown files are not covered.

New source module: `roadmaps.py`. Verification: `python3 -m unittest -q` and `node --check static/app.js`.

## File locations, definitions and version review

Workspaces show full folder paths and **Show in Finder**. The Finder action accepts only a known indexed checkout path, via a same-origin JSON request; it opens Finder without modifying project files.

Hover, focus, or tap view names and status labels for definitions. Multiple distinct task-file contents get an amber warning on the overview and roadmap. **Review versions** lists branches, paths, open/completed item counts, differing recorded statuses, local tracking state, and a source selector. Identical copies are grouped; older distinct contents do not automatically mean unresolved merge conflicts.

**Check task files on GitHub** compares exact file blobs with the current default branch and checks matching file commits on GitHub. Labels distinguish an exact default-branch match, availability in a GitHub commit (possibly historical), and an unverified copy. Local edits are explicitly labelled and a local commit date never implies a push. Checks are read-only, on request, timestamped, and cached for 60 seconds. No files are committed, pushed, merged or deleted by Workboard.


## Permanent home and recovery

Keep the application in a stable local folder so launcher and service paths continue to resolve. Installations may use compatibility symlinks after a move; these are local setup choices, not required repository layout.

The launcher starts a detached background process. Closing the browser or Codex does not control that process. The site is unavailable while the Mac is asleep or off. **Automatic login startup and restart on exit can be enabled** through the user-level macOS launchd service `com.bluelux.workboard`. `Launch Workboard.command` remains a manual fallback and reuses that service. Concurrent launch attempts are locked to prevent duplicate starts.

Click **Service health** in the sidebar, double-click `Check Workboard.command`, or run `python3 check_health.py`. `/api/health` checks the running service independently of source access; `/api/ready` returns 503 until a scan is ready or when degraded. The first scan can take tens of seconds; cached refreshes are faster. A scan exceeding two minutes is reported as degraded. These checks report problems; macOS launchd restarts the server if it exits. A hung but still-running process is reported as degraded and is not automatically killed.

Operational logs are in `.runtime/service.log`, limited to 1 MiB per file with three rotated backups. `.runtime/startup.log` is replaced at each launch. The local move verification receipt is `.runtime/move-receipt.json`.

The Library uses an explicit configuration allowlist, including package manifests, build/lint settings, Docker and deployment files, and GitHub workflows. Markdown instructions, design documents, README files and `tasks/lessons.md` are included. Environment/credential files, lockfiles, dependency folders and generated output are excluded. Files are capped at 2 MiB and 120 candidates per checkout; any discovery limit appears as a warning. Content is displayed as escaped text and is never executed. Full-text search returns at most 60 indexed version matches.

Runtime snapshots, chat/project data, logs, local settings, personal task/correction records and screenshots are excluded from Git. Workboard never commits source projects automatically. Check your checkout with `git status` and `git log -1`. Ignoring a file does not erase its existing Git history.


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

Project AGENTS.md files can map the actual task ledger and supporting artifacts. Cloud environments need the relevant project guidance and cannot be assumed to have a local machine’s global file. Existing chats may retain earlier context. Retiring a file in one checkout does not remove copies in other worktrees.

Library Configuration means build/test/runtime infrastructure, not disposable clutter. Product playbook documents are categorized by role rather than mistaken for agent instructions. Remaining CLAUDE.md copies are labeled legacy guidance; review their source checkout. Historical plans and reports require task-by-task reconciliation before retirement. Personal-tracking removal has been completed; Continue and Reconcile are implemented as prompt handoffs.


### When the framework takes effect

Instructions → Global Codex instructions → Development working agreement shows the lightweight framework read from `~/.codex/AGENTS.md`. Request an instruction change prepares a Codex prompt; Workboard has no settings editor or instruction-save API.

Codex builds its instruction chain at the start of a run. In an older chat, ask Codex to read the current global and project AGENTS.md before continuing; if automatic instructions look stale, start a fresh session/run in the intended project. Restarting does not update files in old checkouts or copy this Mac's global instructions into cloud environments. See [official instruction discovery guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Verification limits: Safari prompt copying, source refresh and removed-worktree continuity have been exercised. Exact Codex links and failure fallbacks are tested, but native foreground navigation into Codex could not be visually confirmed. Instructions displays files available locally, not proof of every chat's effective instruction stack. Cloud-only chats are not covered by the local reader.


## Focused queue and checkout review

Cleanup is a Workboard filter, not a separate tab. In progress lists started/blocked source tasks; Recently completed lists discussions with delivery evidence from the last 30 days. Roadmap retains the full project backlog, Library the documents, Instructions the guidance, and Workspaces the exact local folders. Dashboard counts follow the selected project and search; Git groups and task records remain distinct from discussion counts.

Chat details have one status/action panel, a collapsed evidence section, and the request/response context. Click outside the flyout, press Escape, or use its close button to dismiss it. Clean up session copies the prompt during the click and requests navigation to the exact `codex://threads/...` link. Paste with Command-V and send in Codex; auto-paste and auto-send are not performed. A visible prompt and direct link remain if clipboard access or app opening fails. Browser navigation cannot confirm that Codex actually displayed the destination.

In Workspaces, **Review cleanup in Codex** prepares a prompt limited to the exact indexed checkout and its directly associated temporary branch. Choose a linked chat to copy and open it, or copy only when no appropriate chat is listed. Association does not prove ownership. Codex must inspect fresh state, keep primary checkouts/default branches, preserve unfinished/shared/ignored data, and ask about concrete uncertain targets or deletion approval. The dashboard never deletes folders or creates preservation artifacts.


## Evidence-based next actions

The sidebar explicitly labels **open tasks**, with a project-level breakdown of in-progress/blocked and planned items. This is not the number of unfinished chats or checkouts. The banner names the selected task-file branch, file commit date and version count. The default uses the primary project ledger when available; alternate versions stay visible, and local content is not automatically verified on GitHub.

An exact task-ID match connects a chat to its selected project task record. A recent handoff that conflicts with a Done or Deferred record moves to **Reconcile status**, outside Resume. Historical chats with closed records remain in History; an old chat linked to an open task can appear as **Current task follow-up**, with reconciliation based on that task. The detail shows the dated chat, matched records and exact source path. A file commit date is not a task-completion timestamp. Recent unanswered requests and interrupted turns retain their own priority; mixed scopes remain explicit. Reconciliation verifies later work against code, delivery and original records before restarting anything. It does not automatically mark the chat completed from a checkbox. Task-linked conflicts are prioritized; older unlinked uncertainty remains searchable in History.

Checkout recommendations are independent of chat completion:

- **Keep primary checkout:** retain the shared project home; reconcile unresolved changes in place.
- **Preserve · reconcile work:** changed/untracked files or unique/unverified branch work need investigation before cleanup.
- **Verify delivery · keep for now:** delivery evidence is missing, stale or does not match the checkout tip.
- **Review cleanup:** current matching delivery evidence identifies temporary leftovers; Codex still checks ownership, ignored files, active use and deletion rules.

Chat-folder links describe historical use, not exclusive ownership. The displayed branch is checked out now, not necessarily the branch used by the old chat. Counts of historical chat links are not active-user counts. Recommendation-specific prompts carry the exact folder and evidence into Codex; they never create stashes, backup branches, bundles or another checkout merely to avoid a decision.

## Current work versus chat history

Resume uses dated conversation activity from the last 30 days, not index-update times or changes in a shared folder. Older unfinished-sounding replies, unanswered requests and interruptions stay in History; this does not declare them complete. A currently open PR still appears under Finish delivery, and an explicitly linked open task stays in the project roadmap. Historical outside-main commits alone do not imply unfinished delivery.

The default task-file version is the primary project ledger, with the newest local version used only when no primary ledger is available. Alternate active-checkout versions remain accessible and status disagreements stay visible. Reconcile stale records in the primary source rather than editing an active session's branch copy.

## Always-open signals

The companion adds a compact Git/session strip and a toolbar for **Jump (⌘K / Ctrl+K)**, **Pause**, **Hide screen**, and **Changes**. The expanded overview retains these controls. Git details include changed folders, local branches, cached upstream ahead/behind, observed open PRs, default-branch checks, guarded cleanup candidates and checkpoint-review cues. Missing GitHub access and inventory limits remain visible. PR-head checks, arbitrary GitHub issues and deployment providers without supported evidence are not covered.

**Needs you** promotes recent resume items with explicit requests for your approval/input; it is conservative text matching, not a new task status. Session details show saved activity, estimated context use, compactions seen in the bounded log tail, accumulated session tokens and reported allowance/reset windows. Recent activity is not proof that a process is running. Context is last reported tokens divided by the reported model window, not lifetime consumption or a measure of reasoning quality. Allowance snapshots expire after ten minutes or the reported reset; account identity remains unverified and snapshots are never added across sessions. Cost and unsupported provider usage stay unknown. A 75% context estimate offers a checkpoint-review cue, not automatic rollover.

**Prepare checkpoint & handoff** produces a draft for the existing chat to reconcile its ledger, verification, remaining scope and next step. Review the result before opening a new chat yourself. Workboard sends nothing and never archives sessions. Potential overlap means multiple recently active chats referenced the same exact checkout; it does not establish file ownership.

**Changes** records up to 50 notices in this page's memory: saved replies, changed file-state inventories, PR transitions and newly observed failing default-branch/deployment checks. The first scan is a baseline; reloading clears notices. File content changes that leave the same Git status/path inventory are not detected. No OS notifications or LLM calls are involved. Pause stops this window's polling and display updates, including in-flight responses; other windows may still scan. Hide screen hides the entire dashboard until revealed; it is a visual privacy curtain, not access control, and reloading reveals the dashboard again.

Local scans are requested every **30 seconds while visible** and on manual refresh. In-progress scans are polled approximately every **1.8 seconds**. GitHub evidence uses a **five-minute cache**; the explicit delivery check bypasses it. Usage is only as fresh as the latest saved provider event. No second agent process is started to acquire telemetry.

## Configuration and sharing

Without configuration, all discovered projects appear in the main scope. Copy `workboard.example.json` to the Git-ignored `workboard.local.json`, then replace its `projects` mapping with repository slugs and display names to choose your main projects. Keys match the lower-case final repository name in the origin URL, falling back to the local project name. Other discovered projects remain accessible; this is a presentation filter, not a privacy boundary. Restart the server after changing configuration. `--config /path/to/config.json` selects another file; invalid configuration fails explicitly. Existing personal project aliases were moved into the ignored local file.

For a shareable preview, run `python3 server.py --demo --port 43128` and open `http://127.0.0.1:43128`. Synthetic demo mode reads no personal sources and disables GitHub/Finder actions. Normal mode still uses your local Codex index and existing optional `gh` login. No dependencies were added. See [CONTRIBUTING.md](CONTRIBUTING.md) for verification and adapter boundaries. Before publishing a repository, review its current files and reachable history for private content; these exclusions alone do not sanitize earlier commits. The existing macOS service retains its legacy `com.bluelux.workboard` identifier for compatibility.

Design inspiration: [Omarchy](https://github.com/omacom/omarchy) for consistent workspace controls; [CodexBar](https://github.com/steipete/CodexBar) for usage windows, reset times and source freshness; [Lazygit](https://github.com/jesseduffield/lazygit) for compact summary-to-detail navigation; [btop](https://github.com/aristocratos/btop) for pauseable monitoring. These informed interaction patterns; no source code or dependencies were copied.

The visual companion uses amber for input/changed work, blue for activity/context, violet for branches and teal for allowance/closeout. Dashed circles and hatched bars mean unknown or stale; labels remain available without relying on color. Count tiles are counts, not completion percentages. Context rings and usage bars use recorded measurements. Click a card for the full next step, evidence and handoff controls.

**Direct chat handoff:** Continue and chat-specific Reconcile copy the scoped prompt during the click, then navigate the same window to `codex://threads/<id>`. No preview page or new tab opens on success. Paste and send in Codex yourself. A prompt preview appears only if copying or opening fails; project-wide reconciliation still asks you to choose a chat. Browser/OS external-app approval may still appear.

The local `TASKS.md` remains the canonical development ledger; it is not deleted or renamed. Ignored files are excluded from Workboard’s normal Git-based document discovery, so this local-only ledger is not shown in the dashboard after untracking. Developers can read and maintain it directly.
