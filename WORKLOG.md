# Project worklog

This file is the shared source of truth for cross-device and cross-agent handoffs. Keep the current handoff concise and preserve dated reports as an append-only history.

## Current handoff

- Updated: 2026-08-25 08:45:14 +09:00
- Agent: Codex
- Branch: codex/pr11-feedback-history-source-learning
- Revision: 9dad82f before this checkpoint update
- Objective: Improve daily newsroom reliability around AI/egg translations, food duplicate visibility, feedback export, and source replacement analysis.
- Completed: Added egg category English translation support through the final Anthropic translation path; added feedback JSON copy/download UI; added source feedback/history analysis JSON generation; added near-duplicate validation logs; updated Actions, README, and requirements.
- In progress: Changes are implemented and validated locally but not committed or pushed.
- Blockers and risks: No blocker. Current validation still warns on the checked-in sample/current data because API keys were not used locally, so AI・開発 and egg translated-summary coverage is low until the GitHub Actions run with `ANTHROPIC_API_KEY`.
- Next actions:
  1. Review the PR11 diff, especially `scripts/fetch_rss.py` translation generalization and `scripts/analyze_source_feedback.py`.
  2. Commit the PR11 files if acceptable.
  3. Push `codex/pr11-feedback-history-source-learning` and open a PR.
  4. After merge, run Daily Personal Newsroom manually and inspect `[anthropic]`, `[quality_near_duplicates]`, and `[source_feedback]` logs.
- Validation: Python syntax check passed; unit tests passed (`12 tests`); `scripts/build_site.py` passed; `scripts/validate_newsroom.py` passed with API-key-related translation warnings; `scripts/analyze_source_feedback.py` passed and repeated runs kept the same article snapshot to one history entry.

## Dated work reports

### 2026-09-05 10:45 +09:00 - Claude Code

- Objective: Act on the Codex review findings posted on PR #11.
- Completed work:
  - Reproduced all three findings against the branch code before changing anything.
  - Finding 1: `usable_ai_dev_translation` applied `title_preserves_original_subject` to every category. A fully translated food or egg headline keeps no ASCII token from the English original, so correct translations were rejected. Split the rule into `usable_newsroom_translation(article, category)` gated by `SUBJECT_PRESERVING_CATEGORIES = ("ai_dev",)`, and passed the category at the three candidate-building sites. Every other guard (generic titles, English summaries, boilerplate impact) still applies to all categories.
  - Finding 2: the workflow ran `analyze_source_feedback.py` but never restored the previous `data/run_history.json`, so a clean checkout meant `history_runs=1` forever. Added an `actions/cache@v4` step keyed `newsroom-run-history-${{ github.run_id }}` with a `newsroom-run-history-` restore prefix, so each run restores the newest previous history and always writes a new cache.
  - Finding 3: `build_snapshot` stores the running total of the whole feedback file in every snapshot, and `build_recommendations` summed those totals across runs, so one like was counted once per run. Likes and bads now take the newest snapshot's value; per-run measurements (displayed, score, fallback) are averaged. `fallback_count` became `average_fallback` and `source_recommendation` compares it to `average_displayed` as floats with `>=` instead of `==`, which only worked while history held a single run.
- Affected areas:
  - `scripts/fetch_rss.py`
  - `scripts/analyze_source_feedback.py`
  - `.github/workflows/daily_news.yml`
  - `tests/test_regressions.py`
- Validation:
  - `python -m unittest discover -s tests`: 21 tests, all pass (12 existing plus 9 new covering all three findings).
  - Finding 1, measured: "Company launches plant-based egg product" -> "企業が植物由来の卵商品を発売" was rejected before and is accepted now, while the same translation judged as ai_dev is still rejected and generic or English output is still rejected in both categories.
  - Finding 3, measured: 30 runs over a feedback file holding 3 likes and 1 bad reported 90 likes and 30 bads before, and reports 3 and 1 now. A vote added on the newest run is still picked up, and an all-fallback source is still a replace candidate after 12 runs.
  - Finding 2, measured: running `analyze_source_feedback.py` three times with the history file preserved reports `history_runs=1`, then 2, then 3.
  - `python scripts/score_articles.py` and `python scripts/build_site.py` exit 0.
- Decisions:
  - Chose `actions/cache` over committing the history back to the repository, because the workflow keeps `contents: read` and a daily run keeps the cache warm. History loss to cache eviction resets learning depth but does not break a run.
  - Kept `usable_ai_dev_translation` as a wrapper so existing callers and tests are unchanged.
- Unresolved issues:
  - `validate_newsroom.py` reports `food displayed=9; expected 10` on the committed `data/articles.json` snapshot. This reproduces identically on this branch without these changes and is not related to them.
  - The cache path has not been exercised in a real Actions run.
- Exact next actions:
  1. Run `Daily Personal Newsroom` and confirm the cache step restores history and `history_runs` grows past 1.
  2. Confirm egg translation coverage improves once an Anthropic API key is present.

### 2026-08-25 08:45 +09:00 - Codex

- Objective: Implement the next reliability improvements for translation coverage, feedback accumulation, source replacement analysis, and food duplicate visibility.
- Completed work:
  - Created branch `codex/pr11-feedback-history-source-learning` from `main` at `9dad82f`.
  - Generalized final Anthropic translation candidate selection from AI・開発 only to AI・開発 plus 卵・食品開発.
  - Added category-aware translation prompt guidance so egg/food-development English articles are summarized for product-development use, not AI workflow use.
  - Added browser feedback export controls for copying or downloading the localStorage feedback JSON.
  - Added `scripts/analyze_source_feedback.py` to append stable article snapshots and generate source-level keep/promote/watch/replace recommendations.
  - Added initial `data/run_history.json`, `data/source_recommendations.json`, `public/run_history.json`, and `public/source_recommendations.json`.
  - Added Actions step to generate source feedback artifacts.
  - Added near-duplicate pair logging in `scripts/validate_newsroom.py`, with a food-specific warning threshold.
  - Updated README and requirements to describe feedback export, source analysis, egg translation, and new validation logs.
- Affected areas:
  - `.github/workflows/daily_news.yml`
  - `scripts/fetch_rss.py`
  - `scripts/build_site.py`
  - `scripts/validate_newsroom.py`
  - `scripts/analyze_source_feedback.py`
  - `public/index.html`
  - `public/app.js`
  - `public/style.css`
  - `data/run_history.json`
  - `data/source_recommendations.json`
  - `public/run_history.json`
  - `public/source_recommendations.json`
  - `README.md`
  - `docs/requirements.md`
- Validation:
  - `python -m py_compile scripts/fetch_rss.py scripts/score_articles.py scripts/validate_newsroom.py scripts/analyze_source_feedback.py scripts/build_site.py`: passed using the bundled Codex Python runtime.
  - `python -m unittest discover -s tests -v`: passed, 12 tests.
  - `python scripts/build_site.py`: passed.
  - `python scripts/validate_newsroom.py`: passed with warnings for existing checked-in data where API-backed translations were not present.
  - `python scripts/analyze_source_feedback.py` twice: passed; same article snapshot remained at `history_runs=1`.
  - `node --check public/app.js`: passed.
  - `git diff --check`: passed; Git reported expected LF-to-CRLF working-copy warnings only.
- Decisions:
  - Kept source replacement as recommendation output, not automatic source mutation, to avoid silently changing editorial coverage.
  - Kept run history initialized empty in tracked files; Actions and local runs generate current recommendation JSON from the latest article set.
  - Reused the existing Anthropic tool schema name to minimize API integration churn while making the prompt category-aware.
- Unresolved issues:
  - Local validation cannot prove Anthropic translation quality without `ANTHROPIC_API_KEY`; verify in GitHub Actions after push/merge.
  - `data/feedback.json` is still empty until browser-exported feedback is copied into the repo.
  - Food duplicate detection currently logs near-duplicate pairs; it does not yet suppress or diversify those articles automatically.
- Exact next actions:
  1. Review `git status --short` and the changed files.
  2. Commit the PR11 implementation if the scope is acceptable.
  3. Push `codex/pr11-feedback-history-source-learning` and open a PR.
  4. After the first Actions run, inspect `public/source_recommendations.json`, `public/run_history.json`, and Actions logs for translation and duplicate metrics.

### 2026-08-14 15:33 +09:00 - Codex

- Objective: Install the shared project handoff workflow from `agent-project-workflow` into this repository and prepare an end-of-work checkpoint.
- Completed work:
  - Cloned the workflow template repository outside this repository.
  - Ran `scripts/install-project-workflow.ps1` against this repository.
  - Added shared agent instructions, a project worklog, and local agent skills for resume, checkpoint, and work-report generation.
  - Ran validation proportional to the change.
- Affected areas:
  - `AGENTS.md`
  - `WORKLOG.md`
  - `.agents/skills/resume-project/`
  - `.agents/skills/checkpoint-project/`
  - `.agents/skills/write-work-report/`
- Validation:
  - Python script syntax check: passed (`syntax ok`).
  - `scripts/validate_newsroom.py`: passed.
  - Validation warning remains for AI・開発 translations because API keys were not present; generated output still passes structural validation.
- Decisions:
  - Installed the workflow without `-Force` because no existing workflow files were present.
  - Kept the initial workflow content generic and avoided machine-specific tracked paths.
- Unresolved issues:
  - Workflow adoption files still need to be committed and pushed.
  - The next agent should confirm whether a PR should be opened or updated after push.
- Exact next actions:
  1. Review `git status --short`.
  2. Stage `AGENTS.md`, `WORKLOG.md`, and `.agents/`.
  3. Commit the workflow adoption.
  4. Push `codex/pr8-category-relevance-tuning` to `origin`.
