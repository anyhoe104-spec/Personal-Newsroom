---
name: resume-project
description: Resume work in this repository from the shared project dashboard, the handoff, and the work report. Use when the user says they are starting, resuming, continuing, switching PCs, or asks what to work on next. Read the dashboard review for this project and inspect version-control state before changing files.
---

# Resume project

## 1. Read the local record

1. Resolve the repository root and read `WORKLOG.md` completely when it exists.
2. Inspect `git status --short --branch`, recent commits, and upstream divergence. When the working tree is clean and the branch tracks a remote, fetch before deciding the current synchronization state or whether a pull is appropriate. Do not discard, overwrite, commit, pull, merge, or stash existing changes. Do not pull across local changes; ask before a merge, rebase, branch switch, or conflict resolution.

## 2. Read the project dashboard

3. Locate the dashboard and stop at the first hit: `dashboard.localPaths` in `.agents/project-dashboard.json`, the `PROJECT_DASHBOARD_PATH` environment variable, a sibling `../project-dashboard` checkout, then `dashboard.repository` from the same config read through whatever GitHub access this agent has. Read the dashboard read-only; never edit it while resuming.
4. Identify this project's entry by matching the repository remote URL, repository name, or `project.name` from the config against the dashboard project table. When nothing matches, report that instead of assuming an entry.
5. Read what exists for this project: the `README.md` project table row, `CONTEXT.md`, `projects/<project>.md`, the newest file under `weekly-reports/`, and any other review file that targets this project.
6. Extract phase, priority, status, the latest review with its date and reviewer, the evaluation given, open problems and risks, recommended actions including short spare-time tasks, and anything the review flags as neglected.
7. Check how current the review is. A review older than the newest commits, or one whose stated status disagrees with the repository, is stale: say which parts are outdated rather than repeating them as fact.
8. When the dashboard cannot be reached because no checkout, access, or network is available, say so plainly in the briefing and continue from `WORKLOG.md` and repository evidence. Never invent dashboard content.

## 3. Reconcile, then brief

9. Reconcile the three sources. Repository evidence wins on facts such as what exists, what is committed, what is pushed, and what passes. The dashboard wins on intent such as priority, ordering, and what the owner decided to focus on. `WORKLOG.md` carries the most recent working state between them. Treat commit, revision, and push wording in `WORKLOG.md` as a historical checkpoint snapshot, not the current Git state: a clean branch with no upstream divergence has no pending commit or push even if the report says otherwise. Do not report the checkpoint commit containing `WORKLOG.md`, or its resulting revision change, as a project-state mismatch. Call out only genuine mismatches, uncommitted files, missing dependencies, or an absent upstream.
10. Re-check the handoff's claims about state outside this working tree instead of trusting them. Pull request status, CI results, deployments, and other repositories change while this repository sits still, so these claims are dated observations and go stale on their own. Check the ones the next action depends on. When one proves wrong, say so in the briefing and correct `WORKLOG.md` as part of this session's work rather than leaving the stale line for the next agent.
11. Read files directly related to the next action. Run a quick relevant validation only when safe and useful.
12. Give a compact startup briefing in the user's working language covering:
    - current branch and synchronization state;
    - dashboard status for this project: phase, priority, status, and the date of the latest review;
    - the latest evaluation and the open problems it raised, marking which are already resolved in the repository and which are still open;
    - last completed work, unfinished work, and risks;
    - recommended next action, including the dashboard's recommended actions and its short spare-time tasks.
13. When the user's stated plan conflicts with the dashboard priority, or when the dashboard says this project is deprioritized, say so before starting and let the user decide.
14. Continue when the user's request authorizes implementation. If the user only asked to start or review, stop after the briefing.

Treat `WORKLOG.md` and the dashboard as shared coordination context, not unquestionable truth.
