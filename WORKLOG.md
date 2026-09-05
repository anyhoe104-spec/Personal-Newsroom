# Project worklog

This file is the shared source of truth for cross-device and cross-agent handoffs. Keep the current handoff concise and preserve dated reports as an append-only history.

## Current handoff

- 更新: 2026-09-05 16:26:14 +09:00
- エージェント: Claude Code
- ブランチ: claude/newsroom-weekly-tasks-5msgjt（origin と同期済み）
- リビジョン: b3b304e
- 目的: 今週の改修3件（レビュー指摘の修正 / UI翻訳フックの全体導入 / ログの整理）と、PR #11 のCodexレビュー指摘への対応。
- 完了した作業:
  - PR #11 のCodexレビュー指摘3件を再現確認のうえ修正し、PR #11 は `c6c1e73` として main にマージ済み。
  - 今週の改修3件は PR #12（open）に載せて push 済み。main（PR #11 マージ後）を取り込み、9ファイルの衝突を解消済み。
- 進行中: なし。作業ツリーはクリーンで、push 済み。
- ブロッカーとリスク:
  - 本番 GitHub Actions での実行は未確認。この環境から外部RSSに接続できないため、ログ削減量とrun-historyキャッシュの動作はローカル計測とAPIスタブでの検証にとどまる。
  - リポジトリの `data/articles.json` は2026-06-09のスナップショットで food が9件しかなく、このデータ単体では `validate_newsroom.py` が `food displayed=9; expected 10` で終了コード1になる。`fetch_rss.py` を新規実行すれば4カテゴリとも10件になる。両ブランチより前から存在する事象で、今回変更していない。
- 次のアクション:
  1. `Daily Personal Newsroom` を main で手動実行し、run-historyキャッシュstepが履歴を復元して `history_runs` が1を超えて伸びることを確認する。
  2. 同じ実行のログで、`[rss_summary]` / `[display_summary]` / `[validation_*]` と翻訳ブロックが残り、記事単位のダンプが消えていることを確認する。
  3. PR #12 のマージ可否を判断する。
  4. 多言語化に進む場合は `public/i18n.js` の `MESSAGES` に `en` を追加し、`i18n.setLocale()` を呼ぶ。コンポーネント側の変更は不要。
- 検証: `python -m unittest discover -s tests` 28件パス。`score_articles.py` / `build_site.py` / `analyze_source_feedback.py` 終了コード0。`validate_newsroom.py` は上記の既存事象により1。ヘッドレスChromium 390x844 でUI確認済み。

## Dated work reports

### 2026-09-05 16:26 +09:00 - Claude Code

- 目的: 今週の改修3件の完了と、PR #11 のCodexレビュー指摘への対応、および両者の統合。
- 完了した作業:
  - **レビュー指摘の修正**: 着手時点でGitHub上のPR #1〜#10 にレビューコメント・レビュー・Issueが1件も無かったため、ユーザー確認のうえコード監査に切り替えた。`scripts/score_articles.py` の卵カテゴリ価格ペナルティのキーワードがcp932で二重に文字化けしており「価格」「相場」「卵価」が一度も一致しない状態だったのを `EGG_PRICE_KEYWORDS` として復元。その原因である `console_safe()` の無条件cp932往復を、実際にcp932コンソールの場合のみに限定。RSS取得・失敗ログの二重出力と、`displayed=` を再掲していた `scored=` を削除。`build_site.py` の `category_label` 欠損でのKeyErrorを `.get()` 化。
  - **翻訳フックの全体導入**: `public/i18n.js` を新規追加（`t()` / `tList()` / `setLocale()` / `applyStaticText()` と日本語辞書）。生成HTMLを `data-i18n` / `data-i18n-attr` で注釈し、`public/app.js` から表示文字列を全て除去した。外部ライブラリもビルド手順も追加していない。記事本文（タイトル・要約・impact）は対象外で、Anthropic翻訳パイプラインには触れていない。
  - **ログの整理**: `scripts/newsroom_logging.py` を追加し、パイプライン全体の `print()` を標準 `logging` に移行。記事単位の診断はDEBUG、品質問題はWARNING、API失敗はERROR。`logs/newsroom.log` へのローテーション出力（既定1MiB×3世代）と、記事単位ログの1実行あたり上限（抑制件数を必ず報告）を追加。Actions は `NEWSROOM_LOG_LEVEL=INFO`・ファイル出力なしを明示。
  - **PR #11 のレビュー指摘3件**: 3件とも再現確認のうえ修正し、PR #11 をマージした（`c6c1e73`）。詳細は下の 2026-09-05 10:45 の報告を参照。
  - **PR #11 と PR #12 の統合**: main を PR #12 のブランチに取り込み、9ファイルの衝突を解消。PR #11 の複数カテゴリ翻訳と、本ブランチのログレベル・上限の両方を残した。PR #11 が追加したフィードバック操作の文言も翻訳キー化し、PR #11 が追加した `print()` 4箇所もロガーに移行した。
  - **自分が入れた不具合の修正**: マージコミット `b8e915d` で、翻訳キー化の直後に `git checkout -- public/` を実行して `i18n.js` の `feedback_tools` 辞書と `app.js` の `t()` 呼び出しを破棄したままコミットしていた。生成HTMLだけがキーを参照する状態になり、画面上でボタンが `feedback_tools.copy` などと表示されていた。`b3b304e` で復元し、再発防止のテストを2件追加した。
- 影響範囲:
  - 新規: `scripts/newsroom_logging.py`、`public/i18n.js`
  - 変更: `scripts/fetch_rss.py`、`scripts/score_articles.py`、`scripts/build_site.py`、`scripts/validate_newsroom.py`、`scripts/update_preferences.py`、`scripts/analyze_source_feedback.py`、`scripts/collectors/rss.py`、`scripts/collectors/api_stub.py`、`public/app.js`、`public/index.html`（再生成）、`tests/test_regressions.py`、`.github/workflows/daily_news.yml`、`.gitignore`、`README.md`、`docs/requirements.md`
- 検証:
  - `python -m unittest discover -s tests`: 28件パス（元の12件 + 本ブランチ7件 + PR #11 レビュー修正9件）。
  - `score_articles.py` / `build_site.py` / `analyze_source_feedback.py` 終了コード0。`validate_newsroom.py` は `food displayed=9; expected 10` により1（既存事象）。
  - ログ削減の実測: AI翻訳パス（表示10件・日7/英3、APIスタブ）37行→6行。`build_site.py` 21行→11行。`fetch_rss.py` フル実行（オフライン）115行→78行。`validate_newsroom.py` は14行のまま。`NEWSROOM_LOG_LEVEL=DEBUG` にすると出力は改修前とバイト単位で一致する。
  - ローテーションを `NEWSROOM_LOG_MAX_BYTES=4000 NEWSROOM_LOG_BACKUP_COUNT=2` で確認（3ファイル保持、古い分を削除）。
  - オフライン実行（20ソース全失敗）でコンソールにトレースバックが0件、`logs/newsroom.log` には連鎖例外を含む全文が残ることを確認。
  - ヘッドレスChromium 390x844 で実データ・記事0件フォールバックの両経路を描画。ヘッダー、タブ、カード、原文行、いいね/バッド、PR #11 のコピー/保存操作がすべて辞書から描画され、コンソールエラーなし。
  - 追加した翻訳キーのテストが実際に不具合を検出することを、辞書から `feedback_tools` を削除して確認（壊れていた3キーちょうどを報告）。
- 決定事項:
  - ログ基盤は標準 `logging` を採用し、外部ライブラリを追加しなかった（`requirements.txt` 変更なし）。着手前にユーザーへ確認済み。
  - コンソールのフォーマットは `%(message)s` のままとし、READMEに書かれた `[タグ] 本文` の読み方を維持した。
  - Actions ではファイル出力を無効化した。ランナーは破棄され、GitHubがコンソールログを保持するため、ローテーションはローカル実行向けの機能である。
  - 翻訳フックは新規ファイル1つと `data-i18n` 注釈で実装し、i18nライブラリを導入しなかった。着手前にユーザーへ確認済み。レンダリング構造・DOM構造・カード生成ロジックは変更していない。
  - HTMLには日本語テキストを残した。`i18n.js` の読み込みに失敗しても見出しとボタンは日本語で表示される（記事一覧の描画には従来どおり `app.js` が必要）。
  - カテゴリ名は「AI・活用」に統一した。`config/sources.yaml` が既にその値を持ち、UIに出ている名前であるため。ユーザーの判断による。
  - PR #11 の履歴永続化は commit-back ではなく `actions/cache` を採用した。ワークフローの権限を `contents: read` のまま維持できるため。
  - 本ファイルおよび `docs/work-log-2026-08-08.md` の過去の記録は書き換えていない。これらは当時の名称である「AI・開発」を使っている。
- 未解決の課題:
  - 本番 GitHub Actions での実行が未確認。ログ削減量とrun-historyキャッシュの動作は、ローカル計測とAPIスタブでの検証にとどまる。
  - `data/articles.json` が2026-06-09のスナップショットで food が9件しかなく、`validate_newsroom.py` がこのデータ単体では終了コード1になる。両ブランチより前から存在する事象。
  - PR #12 は open のまま。マージ判断は未了。
  - 多言語ファイル（`en` など）の追加は次段階として未着手。
- 次のアクション:
  1. `Daily Personal Newsroom` を main で手動実行する。
  2. run-historyキャッシュstepが履歴を復元し、`history_runs` が1を超えて伸びることを確認する。
  3. 同じログで `[rss_summary]` / `[display_summary]` / `[validation_*]` と翻訳ブロックが残り、記事単位のダンプが消えていることを確認する。
  4. PR #12 のマージ可否を判断する。

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
