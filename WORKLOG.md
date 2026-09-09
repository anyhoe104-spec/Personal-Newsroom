# Project worklog

This file is the shared source of truth for cross-device and cross-agent handoffs. Keep the current handoff concise and preserve dated reports as an append-only history.

## Current handoff

- 更新: 2026-09-09 +09:00（運用検証の再開後）
- エージェント: Codex (Astra)
- 対象: `codex/newsroom-rss-repair`。ベースはPR #18の `8a35a7b`。
- 完了: 新アプリの実装・UI・PWA・学習・バックアップ。PR #18のReader checksは全工程成功。今回、実RSS取得から生成・検証・ソース分析まで完走し、RSS設定2件と経済の媒体偏りを修正。
- 配送: PR #15 → #16 → #17 → #18 → RSS修正PR。すべて未統合。マージはAGENTS.mdの所有者判断ルールに従う。
- 検証: 実RSSパイプラインは各工程0、40件すべて実記事・重複0。修正先のFood Navigatorは200/20件、Food Business Newsは200/30件。Python34件成功。
- 追加で確認: 現行mainの日次build/deploy成功、履歴キャッシュ復元・history_runs=4。本番の対象20件中18件が日本語表示可能。
- 進行中: なし（実装・検証完了）。配送状態はGitHub上のRSS修正PRを正とする。
- 残課題: HBRの無効RSS、Redditの429、農林水産省の403。今回有効な代替URLを確認できた2媒体だけ修正。個人評価の自動クラウド同期・RSS購読URLの自動変更は対象外。
- 未実施: 新UIのmain統合後のPages確認、Android/iOS実機、ストア申請。
- 次のアクション: 所有者のマージ指示後に依存順で統合し、Daily Personal Newsroom/Pagesを確認する。詳細は `docs/operations-verification.md` と `docs/release-guide.md`。

## Dated work reports

### 2026-09-08 01:20 +09:00 - Claude

- 目的: `<script id="newsData">` への埋め込みエスケープ不足を修正する。2026-08-25 の健全性チェックで検出されてから3週間、`main` に残っていた。
- 完了した作業:
  - `scripts/build_site.py` に `embed_json()` を追加し、`json.dumps(...).replace("<", "\\u003c")` を通してから埋め込むよう変更した。
  - `tests/test_regressions.py` に `ScriptEmbeddingRegressionTests` を追加（3件）。
    - `</script>` を含むタイトルで埋め込み結果に `</script>` と `<img` が現れないこと
    - エスケープ後も `json.loads` が元のオブジェクトに戻ること
    - 日本語がASCIIエスケープされないこと（`ensure_ascii=False` の維持）
- 影響範囲: `scripts/build_site.py`、`tests/test_regressions.py`、`WORKLOG.md`。
- 検証:
  - 修正前のコードで新規テストを実行し、3件が失敗することを確認（意図した不具合を捉えている）。
  - 修正後 `python -m unittest discover -s tests`: 31件 OK。
  - `python scripts/build_site.py`: 終了コード0。生成HTMLの `newsData` ブロックに `</script>` が含まれず、`json.loads` が通ることを確認。生成物はコミットに含めていない。
- 何が問題だったか:
  - 記事のタイトル・要約は外部RSS由来で内容を制御できない。`json.dumps` はJSONとしては正しくエスケープするが、HTMLの `</script>` を無害化しない。
  - タイトルに `</script>` を含む記事が1本でもあると、そこでscript要素が終了し、以降がHTMLとして解釈される。悪意がなくても `JSON.parse` が失敗して記事が1本も表示されなくなり、悪意があれば任意のマークアップを注入できる。
  - このリポジトリはPublicかつ毎日自動デプロイのため、人手の確認が入らない。
  - フロントエンド（`public/app.js`）は `textContent` を徹底して使いXSSを防いでいたが、この1行がその対策を無効化していた。
- 決定:
  - `<` の置換のみで対応した。JSON仕様上 `<` と `\u003c` は等価なので `JSON.parse` の結果は変わらず、`ensure_ascii=False` による日本語のそのまま出力も維持される。
  - インライン置換ではなく名前付き関数 `embed_json()` にした。なぜこの置換が必要かをdocstringに残し、将来 `json.dumps` へ戻されるのを防ぐため。
- 未解決の課題:
  - 本番 Actions での実行確認は未実施（この環境から外部RSSへ接続できないため）。
- 次のアクション: 上記 Current handoff の「次のアクション」を参照。

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

### 2026-09-09 +09:00 — Codex (Astra)

- 目的: 開始スキルで再開し、評価→蓄積→RSSタグ・優先度・提案という設計をアプリ内で利用できる状態に仕上げる。
- 開始時確認: main `f58ecb2`、クリーン。PR #14の安全性修正は統合済み。WORKLOGとproject-dashboardには古い未マージ記録が残っていた。依存ライブラリを導入後、既存31件のテスト成功。
- 完了した作業:
  - `learning.js`: バージョン付き端末内状態、旧評価移行、最新評価の統合・取消、上限付きのカテゴリ別学習、保存容量失敗と破損データの保護、複数タブの更新取得。
  - `app.js` / `i18n.js`: 検索・新着/おすすめ・未読、保存記事、評価履歴、手動関心タグと学習タグ、情報源見直し候補、カテゴリ別活用提案、バックアップ保存/統合・リセット、学習停止・テーマ・簡易表示。
  - 生成HTML/CSS: スマホ1列・PC2列、下部ナビ、設定ダイアログ、44px以上の主要操作、フォーカス、古い記事の注意、サンプルの評価無効化、外部URLの検証。
  - PWA: 相対パスのマニフェスト・192/512pxアイコン、バージョン付きサービスワーカー、オフライン起動、オンライン判定が残っていてもキャッシュ経由を通知。
  - Python: 評価から派生RSSタグ・情報源重みを毎回再計算し、手動編集キーワードを保護。取消を負評価として扱っていた箇所を修正。Actionsで派生タグ計算を実行。
  - テストとCI、要件更新、リリースガイドを追加。
- 検証:
  - `python -m unittest discover -s tests`: 33件成功。
  - `node --test tests/learning.test.cjs`: 7件成功。
  - `python scripts/build_site.py`: 成功。
  - `python scripts/validate_newsroom.py`: 成功。既存スナップショットの翻訳不足・カテゴリ間重複は警告。
  - Playwright操作テスト: 320/390/768/1280px、評価・取消・再読み込み、保存・履歴、検索、タグ、設定、バックアップ・復元、不正JSON、オフライン再読み込み、破損保存を通過。ページエラーなし。
  - 通信不能でもnavigator.onLineがtrueになるブラウザテスト事象から、サービスワーカーのキャッシュ応答に識別ヘッダーを付け、接続案内を補強。
- 決定: 既存の静的GitHub Pages構成を維持。評価は端末内で翌日も反映し、個人評価の公開アップロードを不要にした。RSSの購読URLは自動変更せず、見直し候補として提案する。公開は所有者のマージ判断を待つ。
- CI初回実行: Python33件・Node7件・生成は成功。ブラウザテストがファイル取込完了前に結果を判定して失敗したため、成功/失敗通知を待つよう修正。PR #18で再検証する。
- 未解決/未実施: 本番Actions・Pagesの統合後検証、実機ホーム画面追加、iOS Safari、ストア申請は未実施。ストア審査準拠済みとは表明しない。
- 次のアクション: Current handoffとリリースガイドを参照。ソース変更・テスト・ドキュメントをコミットし、最終ブランチ/PRと配送内容の一致を確認する。

### 2026-09-09 +09:00 — Codex (Astra)、運用検証の再開

- 目的: 「再開して」の指示を受け、公開前の実RSS・運用確認を進める。
- 開始確認: PR #15〜#18は未統合。`codex/newsroom-release` はoriginと同期・クリーン。Reader checks run 34300223430は全工程成功。
- 完了:
  - 現行mainの日次run 34288778211でbuild/deploy成功、キャッシュ復元・history_runs=4、対象20件中18件の日本語表示を確認。
  - 検証用コピーで実RSS→スコア→生成→validator→ソース分析を実行し、すべて終了コード0。283記事から40件の実記事を選定し、重複0件。
  - Food Navigatorの404を公式の現行XMLフィードへ修正。HTTP200・20記事。
  - Food Business NewsのHTML案内URLを公式のFBN Best News XMLへ修正。HTTP200・30記事。
  - 経済10本が1媒体へ偏る結果を受け、同一媒体6件の目安を追加。他媒体不足時は10件確保を優先する既存の二段階選定を維持。
  - 運用確認レポートを追加。
- 影響範囲: config/sources.yaml、scripts/score_articles.py、tests/test_learning.py、docs/operations-verification.md、WORKLOG.md。
- 検証: Python34件成功。新規回帰は経済の6/4媒体配分と単一媒体の10件確保を確認。URL修正後の2フィードは個別HTTP/XML検証。全パイプラインは修正前設定で完了したため、修正後の全件再取得を済ませたとは表明しない。
- 決定: 確認できた公式配信先だけを修正。HBRの代替候補は502のため採用しない。制限の回避は行わない。
- 未解決: HBR・Reddit429・農林水産省403。本番新版公開、実機、ストア申請は未実施。
- 次のアクション: RSS修正PRを配送し、所有者のマージ判断を得てから本番反映を確認する。
