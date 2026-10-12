# Workboard charter

## Purpose

Help the user return after interruptions, understand unfinished work across BlueLux coding projects, and bring each work unit to a clear conclusion. Make it easy to resume, finish delivery, reconcile project records, and remove verified temporary leftovers through the appropriate Codex session.

The home screen should answer: What remains open? What evidence supports that? Where do I continue? What can be closed out? Recent activity provides context; it is not the primary queue.

## Source of truth

| Question | Authoritative evidence |
| --- | --- |
| What was requested or decided? | The relevant Codex conversation and recorded project decisions |
| What work is planned or remains? | The project's designated task ledger and supporting plans |
| What has been implemented and verified? | Code, relevant tests and actual verification results |
| Has this work been delivered? | Its exact commit or PR verified on GitHub's current default branch |
| Is deployment healthy? | Deployment/runtime evidence, separately from delivery |
| What temporary material remains? | Fresh inspection of exact branches, worktrees and files, with ownership evidence |

Workboard presents one recommended next action with observations, provenance, timestamps and gaps. Historical chat ownership, current checkout state and task-file status are distinct. An old unfinished-work statement cannot silently override a closed task record; route the conflict to source reconciliation before resuming. It does not become another task ledger. Source conflicts are visible and reconciled in the source project, not concealed with dashboard overrides. A stale checkbox is recorded intent, not proof that implementation remains unfinished.

## View-only contract

The intended product has no personal tracking layer: no manual completion/parking/focus overrides, saved next-step notes, or independently maintained task statuses. Search, filters, document browsing, prompt copying, source links and Finder reveal are appropriate interactions. Disposable caches and bounded operational logs may support the reader; they must not become authoritative workflow records.

Current implementation: statuses are derived from sources. Manual choices and next-step notes have been removed, and Continue/Reconcile/Clean up are draft-only handoffs into Codex.

Workboard never writes Codex databases or source projects, sends messages, commits, pushes, merges, deploys, or deletes workspaces. Prompt actions copy a reviewable draft and open the identified existing chat. The user sends it in Codex, where the project's instructions and normal authorization apply. A click must not silently submit it.

## Work states

- **Resume:** evidence of unfinished execution or a later request, including interrupted work and undelivered local changes. Repository membership alone does not assign work to a chat.
- **Finish delivery:** a concrete remaining verification, push, review or merge step for a work unit. Feature-branch pushes are not default-branch delivery.
- **Project follow-up:** outstanding obligations in task files or plans, with their source and version visible.
- **Recently completed:** the identified work unit is verified on the current GitHub default branch. Later requests in the same chat can remain open.
- **Cleanup:** verified delivered work has specific temporary leftovers. Completion and cleanup are independent.
- **Reconcile / verify:** evidence is unavailable, ambiguous or conflicting. This is not an invented task status or permission to discard work.

Use the repository's actual default branch, including master where applicable. Absence of a local checkout is neutral for a finished chat. Preserve access and project association without creating a replacement checkout. Cloud-only or unavailable evidence must remain unknown, never silently interpreted as clean or complete.

## Minimal prompt actions

Prefer one relevant primary action per item, supported by readable evidence, rather than a toolbar of workflow controls.

- **Continue:** resume the identified unfinished work using the latest request and source state. Avoid restarting completed work or inventing a new project.
- **Reconcile:** inspect the project's designated task ledger, relevant README, plans and configuration guidance against actual implementation, decisions and delivery. Correct supported discrepancies in those original sources under the project's rules.
- **Clean up:** inspect and remove only verified disposable leftovers attributable to the selected session, under applicable deletion rules.

Reconcile can target a project, a conflicting task/chat record, or unresolved work in one exact checkout. Its scope must identify the project, artifact versions and relevant session. Shared folders and recency alone do not establish session ownership. If routing or authority is unclear, explain the gap and request the concrete missing choice in Codex.

Reconciliation distinguishes completed work, outstanding verification, deferred work, superseded plans and genuinely unknown status. Update relevant existing documents and cross-links; do not manufacture new reports or duplicate ledgers. Age alone does not make a plan obsolete. A merged feature does not complete every task in its parent initiative. Orphaned files are candidates for review, not automatic deletion.

Neither reconciliation nor cleanup should create stashes, backup branches, recovery bundles, replacement checkouts or WIP commits merely to avoid a decision. Preserve ambiguous/user-authored work in place and ask about exact unresolved items. Do not expand session cleanup into a repository-wide sweep.

## Lightweight development workflow

The shared workflow is: orient, implement, verify, reconcile. Plan proportionately for substantial work; keep small changes small. During normal authorized work, update the affected task status, acceptance criteria and documentation at meaningful milestones and before declaring completion. If deliberately pausing, record a useful next step in the existing project ledger. An abrupt interruption cannot guarantee that checkpoint occurred.

A Reconcile action repairs accumulated drift; it does not replace routine maintenance. No mandatory GStack chain, parallel review ceremony, background repository sweep or new document per change is required. Changes to policy, delivery and deletion retain their own scope and authorization.

## Success criteria

The user can identify unfinished work, its project and the next useful session without maintaining Workboard itself. Every status explains its evidence and freshness. Corrections land in original project sources and appear on refresh. Completed work remains discoverable without crowding the resume queue. No additional cleanup burden is created by the dashboard.

This charter describes product intent. AGENTS.md describes agent behavior; TASKS.md records implementation work. CHARTER.md is not a special auto-loaded Codex instruction filename.
