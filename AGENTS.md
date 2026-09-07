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
- **When a push is authorized, finish the delivery: open or update a pull request for that branch in the same step.** A draft pull request is acceptable. Never leave an authorized push without a corresponding pull request — a branch with no pull request has no reviewer and no path to `main`.
- **Merging stays the owner's decision.** Agents never merge and never request review on the owner's behalf unless asked.
- **Keep a pull request reviewable in one sitting.** When a change would exceed roughly 500 changed lines, split it into separate branches and pull requests along natural boundaries, and say in each description which part it covers.
- In the pull request description, state what changed, which checks were run and their results, and what was deliberately left out.
- Before committing, summarize included files. Before pushing, confirm the expected remote and branch.
- Never put secrets, credentials, or machine-specific absolute paths in tracked reports.
