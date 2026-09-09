# Agent instructions

These instructions apply to every agent working in this repository, whether or not the agent supports Codex skills.

## Start or resume work

1. Read `WORKLOG.md` completely when it exists.
2. Read the project dashboard for this project before editing anything. See `Project dashboard` below.
3. Inspect the current branch, working tree, recent commits, and upstream state before editing.
4. Reconcile the report and the dashboard review with repository evidence. Repository evidence wins on facts; the dashboard wins on priority and intent.
5. Re-check, rather than trust, the report's claims about state outside this working tree. Correct any that have gone stale.
6. State the last completed work, unfinished work, risks, the open problems raised by the latest review, and the recommended next action.
7. When supported, use `$resume-project` from `.agents/skills/resume-project`.

## Project dashboard

1. The dashboard is a separate repository that holds the cross-project table, the per-project review notes, and the weekly reports. Locate it in this order: `dashboard.localPaths` in `.agents/project-dashboard.json`, the `PROJECT_DASHBOARD_PATH` environment variable, a sibling `../project-dashboard` checkout, then `dashboard.repository` read through available GitHub access.
2. Read the project table row for this repository, `CONTEXT.md`, `projects/<project>.md`, and the newest weekly report. Take from them the phase, priority, status, latest evaluation, open problems, and recommended actions.
3. Treat a review as stale when it is older than the newest commits or disagrees with the repository. Say which parts are outdated instead of repeating them.
4. When the dashboard is unreachable, say so and continue from `WORKLOG.md` and repository evidence. Never invent review content.
5. Read the dashboard read-only. Do not edit or commit dashboard files unless the user asks for that specifically.

## Pause, finish, or hand off work

1. Run relevant validation in proportion to the changes.
2. Update `WORKLOG.md` before stopping: rewrite `Current handoff`, then append one dated report containing the acting agent, objective, completed work, affected areas, validation, decisions, unresolved issues, and exact next actions.
3. Record what did not work: approaches tried and abandoned and why, output that was wrong and had to be corrected, assumptions that turned out to be false, and roughly how many attempts a step took. Name the wrong answer, not only the right one.
4. Mark every claim about state outside this working tree — pull request status, CI results, deployments, other repositories — with when it was checked and how. These change without this repository changing, so an unmarked claim cannot be told apart from a current fact.
5. Record which of the dashboard's open problems for this project were addressed and which remain.
6. Preserve all previous dated entries. Never claim an unrun check passed or conceal incomplete or failing work.
7. When supported, use `$checkpoint-project` from `.agents/skills/checkpoint-project`.

## Work-report articles

1. Treat `WORKLOG.md` and repository evidence as factual sources.
2. Write derived articles under `docs/work-reports/` unless the user specifies another destination.
3. Separate verified facts from interpretation and do not present unfinished work as complete.
4. Use the record of what did not work. It is usually the most informative material an article has.
5. Confirm a defect's fix has shipped before describing the defect. Do not publish the details of an unfixed defect in a project that is publicly reachable.
6. Do not rewrite `WORKLOG.md` merely to improve an article.
7. When supported, use `$write-work-report` from `.agents/skills/write-work-report`.

## Git safety

- Do not discard or overwrite existing user or agent changes.
- Do not commit, push, merge, rebase, switch branches, or resolve conflicts unless the user has authorized that action.
- **When a push is authorized, finish the delivery: open or update a pull request for that branch in the same step.** A draft pull request is acceptable. Never leave an authorized push without a corresponding pull request — a branch with no pull request has no reviewer and no path to `main`.
- **Merging stays the owner's decision.** Agents never merge and never request review on the owner's behalf unless asked.
- **Keep a pull request reviewable in one sitting.** When a change would exceed roughly 500 changed lines, split it into separate branches and pull requests along natural boundaries, and say in each description which part it covers.
- In the pull request description, state what changed, which checks were run and their results, and what was deliberately left out.
- Before committing, summarize included files. Before pushing, confirm the expected remote and branch.
- Never put secrets, credentials, or machine-specific absolute paths in tracked reports.
