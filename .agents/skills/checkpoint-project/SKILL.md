---
name: checkpoint-project
description: End, pause, or hand off work in this repository by updating its shared handoff and dated agent work report. Use when the user says they are stopping, finishing for today, switching PCs, recording progress, or preparing work for another agent.
---

# Checkpoint project

1. Resolve the repository root and inspect the current branch, working tree, diff, recent commits, and upstream state.
2. Run relevant tests or checks in proportion to the changes. Record commands and outcomes accurately; never claim an unrun check passed.
3. Create `WORKLOG.md` at the repository root if absent, with `Current handoff` and `Dated work reports` sections.
4. Rewrite `Current handoff` to reflect actual project state, including updated time and timezone, agent, objective, completed work, work in progress, blockers or risks, exact next actions, validation, branch, and revision when applicable. Treat the revision as the project-work revision before this checkpoint update and label it accordingly; the checkpoint commit itself cannot be known while writing the file.
5. Append exactly one dated report using local date/time and timezone. Identify the acting agent, preserve previous reports, and include objective, completed work, affected areas, validation, decisions, unresolved issues, and exact next actions. Use the user's working language unless the repository establishes another reporting language.
6. Record what did not work, as a required part of the dated report. Include approaches tried and abandoned and why, output that was wrong and had to be corrected, assumptions that turned out to be false, and roughly how many attempts a step took. Name the wrong answer, not only the right one: "the first fix escaped the wrong character" carries information that "fixed the escaping" does not. A report containing only what succeeded misstates the work and discards the only record of how the result was reached.
7. Mark every claim about state outside this working tree with when it was checked and how. Pull request status, CI results, deployments, other repositories, and external services all change without this repository changing, so an unmarked claim cannot be told apart from a current fact. Write "PR #14 unmerged (checked 2026-09-08 01:20 via the pull request page)", not "PR #14 unmerged".
8. When the project dashboard lists open problems for this project, record in the handoff which of them this session addressed and which remain, so the next dashboard review starts from current facts. Do not edit the dashboard unless the user asks for that.
9. Recheck changes after updating the report. Exclude secrets, credentials, machine-specific absolute paths, and irrelevant generated files.
10. Keep transient checkpoint mechanics out of `WORKLOG.md`: do not record this report update as "uncommitted" or "unpushed" merely because it has not yet been committed or pushed. Record a genuinely pending project change only when it is intended to remain after the checkpoint workflow finishes.
11. Do not commit or push unless explicitly authorized. Before committing, summarize included files. Before pushing, confirm the expected remote and branch and ensure no unresolved conflicts remain. After any authorized commit or push, recheck Git and report its actual result in the final response; do not modify `WORKLOG.md` again solely to record the commit or push that contains it.
12. Finish with a concise handoff summary covering completed and remaining work, validation, actual commit/push status from the final Git check, and how the next agent should resume.

Never conceal unfinished or failing work. A checkpoint remains useful when implementation is incomplete.
