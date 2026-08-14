# Agent instructions

These instructions apply to every agent working in a repository that adopts this workflow, whether or not the agent supports Codex skills.

## Start or resume work

1. Read `WORKLOG.md` completely when it exists.
2. Inspect the current branch, working tree, recent commits, and upstream state before editing.
3. Reconcile the report with repository evidence. Repository evidence wins when they differ.
4. State the last completed work, unfinished work, risks, and recommended next action.
5. When supported, use `$resume-project` from `.agents/skills/resume-project`.

## Pause, finish, or hand off work

1. Run relevant validation in proportion to the changes.
2. Update `WORKLOG.md` before stopping: rewrite `Current handoff`, then append one dated report containing the acting agent, objective, completed work, affected areas, validation, decisions, unresolved issues, and exact next actions.
3. Preserve all previous dated entries. Never claim an unrun check passed or conceal incomplete or failing work.
4. When supported, use `$checkpoint-project` from `.agents/skills/checkpoint-project`.

## Work-report articles

1. Treat `WORKLOG.md` and repository evidence as factual sources.
2. Write derived articles under `docs/work-reports/` unless the user specifies another destination.
3. Separate verified facts from interpretation and do not present unfinished work as complete.
4. Do not rewrite `WORKLOG.md` merely to improve an article.
5. When supported, use `$write-work-report` from `.agents/skills/write-work-report`.

## Git safety

- Do not discard or overwrite existing user or agent changes.
- Do not commit, push, merge, rebase, switch branches, or resolve conflicts unless the user has authorized that action.
- Before committing, summarize included files. Before pushing, confirm the expected remote and branch.
- Never put secrets, credentials, or machine-specific absolute paths in tracked reports.
