---
name: write-work-report
description: Turn this repository's WORKLOG.md and verifiable project evidence into an accurate development report article. Use when the user asks for a daily, weekly, milestone, technical, stakeholder, retrospective, or public-facing work report based on agent activity.
---

# Write work report

1. Resolve the repository root and read `WORKLOG.md` completely.
2. Determine the requested date range, audience, purpose, tone, and output destination. If unspecified, use the latest dated entry, a concise internal-development audience, and `docs/work-reports/YYYY-MM-DD-development-report.md`.
3. Verify material claims against relevant commits, diffs, tests, and project files. Treat the worklog as a coordination record, not infallible evidence.
4. Write a standalone article in the user's working language with title and covered period, objective and context, completed work and outcomes, important decisions and rationale, validation and limitations, and unresolved issues, risks, and next steps.
5. Adapt detail to the audience. Explain jargon for nontechnical readers; include component or test details for technical readers.
6. Clearly distinguish verified facts, unverified agent-recorded statements, and interpretation. Never invent metrics, dates, tests, decisions, or completion status.
7. Do not expose secrets, credentials, private personal data, or machine-specific absolute paths. Do not modify `WORKLOG.md` solely to improve the article.
8. Preserve existing articles unless the user requests an update. Report the output path and evidence range used.
