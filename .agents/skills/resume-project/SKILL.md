---
name: resume-project
description: Resume work in this repository from its shared handoff and work report. Use when the user says they are starting, resuming, continuing, switching PCs, or asks what to work on next. Inspect version-control state and WORKLOG.md before changing files.
---

# Resume project

1. Resolve the repository root and read `WORKLOG.md` completely when it exists.
2. Inspect `git status --short --branch`, recent commits, and upstream divergence. Do not discard, overwrite, commit, pull, merge, or stash existing changes.
3. Compare repository evidence with `Current handoff` and the latest dated report. Repository evidence wins when they disagree. Call out mismatches, uncommitted files, missing dependencies, or an absent upstream.
4. If the working tree is clean and the branch tracks a remote, fetch before deciding whether a pull is appropriate. Do not pull across local changes. Ask before a merge, rebase, branch switch, or conflict resolution.
5. Read files directly related to the next action. Run a quick relevant validation only when safe and useful.
6. Give a compact startup briefing in the user's working language containing current branch and synchronization state, last completed work, unfinished work and risks, and the recommended next action.
7. Continue when the user's request authorizes implementation. If the user only asked to start or review, stop after the briefing.

Treat `WORKLOG.md` as shared coordination context, not unquestionable truth.
