# Project worklog

This file is the shared source of truth for cross-device and cross-agent handoffs. Keep the current handoff concise and preserve dated reports as an append-only history.

## Current handoff

- Updated: 2026-09-05 11:05 +09:00
- Agent: Claude Code
- Branch: claude/newsroom-weekly-tasks-5msgjt
- Objective: Merge the weekly maintenance branch with the newly merged PR #11 work.
- Completed: PR #11 was reviewed by Codex, all three findings were fixed and pushed, and the PR was merged into `main` as `c6c1e73`. The weekly maintenance branch (review fixes, the UI translation hook, and the logging migration) is being merged with that `main`.
- In progress: Resolving the merge of `origin/main` into `claude/newsroom-weekly-tasks-5msgjt` for PR #12. Nine files overlapped; the resolution keeps PR #11's multi-category translation behaviour and PR #12's logging levels and translation keys together.
- Blockers and risks: `data/articles.json` in the repository is a 2026-06-09 snapshot with only 9 food articles, so `validate_newsroom.py` reports `food displayed=9; expected 10` on the committed data alone. A fresh `fetch_rss.py` run fills all four categories. This predates both branches.
- Next actions:
  1. Finish and validate the merge, then push PR #12.
  2. Run `Daily Personal Newsroom` on `main` and confirm the run-history cache restores and `history_runs` grows past 1.
  3. Confirm on the same run that the Actions log is shorter while `[rss_summary]`, `[display_summary]`, `[validation_*]` and the translation block still appear.
- Validation: see the dated reports below for the measurements taken on each branch.

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

### 2026-08-31 12:53 +09:00 - Claude Code

- Objective: Weekly maintenance covering review findings, a UI translation hook, and log volume control.
- Completed work:
  - Reviewed the repository for the "recent review findings" item. No review comments, reviews or issues exist on PR #1-#10 or in the issue tracker; the user confirmed to substitute an audit of the current code.
  - Fixed the egg price penalty in `scripts/score_articles.py`: its keywords had been round-tripped through cp932 twice and were stored as mojibake, so "価格", "相場" and "卵価" could never match. Restored as `EGG_PRICE_KEYWORDS` with a regression test.
  - Fixed `console_safe()` in `scripts/fetch_rss.py`, which forced every log line through a cp932 round trip on all platforms. It now only does so on a real cp932 console. This was the mechanism that produced the mojibake above.
  - Removed the duplicated per-source fetch/failure log lines in `main()` and the `scored=` field that repeated `displayed=` in both run summaries.
  - Hardened `build_site.py` against an article without `category_label`.
  - Added `scripts/newsroom_logging.py` and converted all 94 `print()` call sites across the pipeline to standard `logging` with levels. Per-article translation diagnostics are DEBUG, quality problems WARNING, API failures ERROR. Console format is unchanged.
  - Added a rotating file handler (`logs/newsroom.log`, 1 MiB x 3 by default) and `log_capped()` so repetitive per-article groups cannot flood a run; suppressed counts are reported.
  - Added `public/i18n.js` with `t()` / `tList()` / `setLocale()` / `applyStaticText()` and a Japanese dictionary. Annotated the generated HTML with `data-i18n` / `data-i18n-attr` and removed every display string from `public/app.js`.
  - Aligned the category name on `config/sources.yaml`: README, `docs/requirements.md`, the validator warning and the UI fallback dataset now all say AI・活用.
- Affected areas:
  - `scripts/newsroom_logging.py` (new), `scripts/fetch_rss.py`, `scripts/score_articles.py`, `scripts/build_site.py`, `scripts/validate_newsroom.py`, `scripts/update_preferences.py`, `scripts/collectors/rss.py`, `scripts/collectors/api_stub.py`
  - `public/i18n.js` (new), `public/app.js`, `public/index.html` (regenerated)
  - `tests/test_regressions.py`, `.github/workflows/daily_news.yml`, `.gitignore`, `README.md`, `docs/requirements.md`
- Validation:
  - `python -m unittest discover -s tests`: 17 tests, all pass (12 existing plus 5 new for the price keywords, the log caps and `console_safe`).
  - Full offline pipeline run: `fetch_rss.py`, `score_articles.py`, `build_site.py`, `validate_newsroom.py` all exit 0. Outbound RSS is blocked in this environment, so every source failed and all categories fell back to sample articles; the AI translation path was exercised separately with a stubbed Anthropic response.
  - Log volume, AI translation path (10 display articles, 7 JA / 3 EN, stubbed API): 37 console lines before, 6 after. At `NEWSROOM_LOG_LEVEL=DEBUG` the output is byte-identical to the previous behaviour.
  - Log volume, offline full fetch run: 115 console lines before, 78 after. `build_site.py`: 21 before, 11 after. `validate_newsroom.py`: unchanged at 14.
  - Rotation verified with `NEWSROOM_LOG_MAX_BYTES=4000 NEWSROOM_LOG_BACKUP_COUNT=2`: three files kept, oldest discarded.
  - UI verified in headless Chromium at 390x844 against both the live-data and the empty-data fallback path. Header, tabs, cards, the 原文 line, feedback buttons and localStorage persistence match the previous rendering, with no console or page errors.
- Decisions:
  - Used the Python standard library `logging` rather than an external logging package, so `requirements.txt` is unchanged. Confirmed with the user before starting.
  - Kept the console formatter as `%(message)s` so the `[tag] message` shape documented in README stays valid and existing log-reading habits keep working.
  - Actions runs pin `NEWSROOM_LOG_LEVEL=INFO` and disable file logging, because the runner is discarded and GitHub already stores the console log. Rotation matters for local runs.
  - Implemented the translation hook as a single new file with `data-i18n` annotations rather than an i18n library, keeping the build-free static-Pages setup and leaving rendering, DOM structure and card generation untouched. Confirmed with the user before starting.
  - Left the Japanese text inline in the markup so the page degrades to readable Japanese if `i18n.js` fails to load.
  - The translation hook covers UI chrome only. Article titles, summaries and impact still come from `data/articles.json`, and the Anthropic translation pipeline was not modified. Confirmed with the user.
  - Aligned the category name to AI・活用 on the user's decision, since `config/sources.yaml` already carried it and it is what the UI shows.
  - Did not rewrite the historical entries in this file or in `docs/work-log-2026-08-08.md`, which still refer to the category as AI・開発.
- Unresolved issues:
  - `data/articles.json` in the repository is a 2026-06-09 snapshot with 9 food articles, so `validate_newsroom.py` reports `food displayed=9; expected 10` and exits 1 on the committed data alone. A fresh fetch fills the category. Pre-existing, unchanged by this branch.
  - The branch has not been exercised in GitHub Actions, so the production log reduction is measured locally and with a stubbed API rather than observed in a real run.
  - No pull request has been opened.
- Exact next actions:
  1. Run `Daily Personal Newsroom` manually on `claude/newsroom-weekly-tasks-5msgjt`.
  2. Confirm in that run's log that `[rss_summary]`, `[display_summary]`, `[validation_summary]` and the AI translation block are still present and the per-article dumps are gone.
  3. Decide whether to open a pull request.

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
