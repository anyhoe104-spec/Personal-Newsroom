---
name: checkpoint-project
description: End, pause, or hand off work in this repository by updating its shared handoff and dated agent work report. Use when the user says they are stopping, finishing for today, switching PCs, recording progress, or preparing work for another agent.
---

# Checkpoint project

1. Resolve the repository root and inspect the current branch, working tree, diff, recent commits, and upstream state.
2. Run relevant tests or checks in proportion to the changes. Record commands and outcomes accurately; never claim an unrun check passed.
3. Create `WORKLOG.md` at the repository root if absent, with `Current handoff` and `Dated work reports` sections.
4. Rewrite `Current handoff` to reflect actual state, including updated time and timezone, agent, objective, completed work, work in progress, blockers or risks, exact next actions, validation, branch, and revision when applicable.
5. Append exactly one dated report using local date/time and timezone. Identify the acting agent, preserve previous reports, and include objective, completed work, affected areas, validation, decisions, unresolved issues, and exact next actions. Use the user's working language unless the repository establishes another reporting language.
6. Recheck changes after updating the report. Exclude secrets, credentials, machine-specific absolute paths, and irrelevant generated files.
7. Do not commit or push unless explicitly authorized. Before committing, summarize included files. Before pushing, confirm the expected remote and branch and ensure no unresolved conflicts remain.
8. Finish with a concise handoff summary covering completed and remaining work, validation, commit/push status, and how the next agent should resume.

Never conceal unfinished or failing work. A checkpoint remains useful when implementation is incomplete.
