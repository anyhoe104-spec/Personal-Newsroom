# Project worklog

This file is the shared source of truth for cross-device and cross-agent handoffs. Keep the current handoff concise and preserve dated reports as an append-only history.

## Current handoff

- 更新: 2026-09-09 14:47:39 +09:00
- エージェント: Claude Code
- ブランチ: claude/record-fetch-rss-duplicate-defs（main = cb5c25c から作成）
- 目的: 設定層の分離（`docs/config-separation-plan.md`）。Step 1 を完了し、作業中に見つけた既存不具合を記録する。
- 完了した作業:
  - Step 1（エンジンを設定非依存にする）を PR #20 として実施し、`cb5c25c` で main にマージ済み。
  - `NEWSROOM_CONFIG_DIR` / `NEWSROOM_STATE_DIR` と、フィードURLの `url_env` 注入経路を導入。既定値は従来の配置のため挙動は不変。
  - 注入されたURLがログに平文で出る漏洩を発見し、ログ層の伏せ字で塞いだ。
- 進行中: 本ブランチは `scripts/fetch_rss.py` の重複定義に関する記録の追加のみ。コード変更はしない。
- ブロッカーとリスク:
  - **`scripts/fetch_rss.py` に同名関数の重複定義が3組ある**（下の「未解決の課題」に詳細）。前半の定義は到達せず、そこを修正しても何も起きない。オーナーの判断で対応を保留中。
  - 本番 GitHub Actions での実行は未検証のまま。この環境から外部RSSに接続できないため、ログ削減量と run-history キャッシュの動作はローカル計測とスタブ検証にとどまる。
  - `data/articles.json` は2026-06-09のスナップショットで food が9件しかなく、このデータ単体では `validate_newsroom.py` が終了コード1になる。`fetch_rss.py` の新規実行で解消する。Step 1 以前から存在する事象。
- 次のアクション:
  1. 計画書の Step 2（`themes/example/` のサンプルテーマパック）に着手する。
  2. `fetch_rss.py` の重複定義を削除するか否かを判断する（保留中）。
  3. `Daily Personal Newsroom` を main で手動実行し、Step 1 のログ出力（`[source_config] config_dir=...`）と既存の確認項目を実機で確認する。
- 検証: Step 1 時点で `python -m unittest discover -s tests` 52件パス。環境変数なしでパイプライン出力が Step 1 前と一致することを確認済み。

## Dated work reports

### 2026-09-09 14:47 +09:00 - Claude Code

- 目的: 設定分離 Step 1 の完了と、作業中に見つけた既存不具合の記録。
- 完了した作業:
  - `docs/config-separation-plan.md` の Step 1 を実施し、PR #20 として main にマージした（`cb5c25c`）。
    - `scripts/newsroom_config.py` を追加し、設定と学習データの場所を決める唯一の場所にした。`NEWSROOM_CONFIG_DIR`（既定 `config/`）と `NEWSROOM_STATE_DIR`（既定 `data/`）。パイプライン6スクリプトの `ROOT / "config"` / `ROOT / "data"` 直書きを全廃した。
    - フィードURLを `sources.yaml` に書かず環境変数から注入する経路を用意した。`url_env` の参照名を、①同名の環境変数 → ②`GOOGLE_ALERT_FEEDS`（JSONオブジェクト）→ ③同項目の `url` の順で解決する。解決できないソースは参照名だけを記した警告つきでスキップし、実行は継続する。
    - 5本のGoogleアラートに参照名を付けつつ既存の `url` も残した。今日の挙動は同一で、Step 4 / Step 6 では値を消すだけで済む。
  - 検証中に、注入したURLがログに平文で出ることを確認したため、計画書には無いが Step 1 に含めて塞いだ。requests は失敗時に `Max retries exceeded with url: /alerts/feeds/<id>/<token>` の形でホストとパスを分けて出力し、GitHub の Secret マスクは完全一致でしか効かないため、公開Actionsログにパスが残る。`newsroom_logging` に伏せ字用の Formatter を追加し、`newsroom_config` が注入されたURLとそのパスを登録する。`sources.yaml` 直書きのURLは秘密ではないため対象外とした。
- 影響範囲:
  - 新規: `scripts/newsroom_config.py`
  - 変更: `scripts/fetch_rss.py`、`scripts/score_articles.py`、`scripts/build_site.py`、`scripts/validate_newsroom.py`、`scripts/update_preferences.py`、`scripts/analyze_source_feedback.py`、`scripts/newsroom_logging.py`、`config/sources.yaml`、`tests/test_regressions.py`、`README.md`、`docs/requirements.md`
- 検証:
  - `python -m unittest discover -s tests`: 52件パス（Step 1 前の main は31件、新規21件）。
  - 伏せ字の Formatter を無効化すると、伏せ字テスト3件だけが落ちることを確認した。
  - 環境変数なしで `score_articles.py` / `validate_newsroom.py` / `analyze_source_feedback.py` の出力が Step 1 前の main とバイト単位で一致。`build_site.py` は出力先の絶対パス表示のみ差分（チェックアウト位置の違い）。
  - リポジトリ外のテーマパックに対して実行し、外部の `sources.yaml` を読み、`run_history.json` と `source_recommendations.json` を外部側に書き、リポジトリの `data/` が無変更であることを確認した。
  - ダミーのアラートURLで漏洩を再現し、修正後はコンソールと `logs/newsroom.log` の両方で0件になることを確認した。
- 決定事項:
  - Step 1 では注入の**経路**を用意するに留め、`sources.yaml` から実URLは削除しなかった。削除は計画書の Step 6 の担当であり、Step 1 の「この時点ではまだ挙動は変わらない」という前提を守るため。
  - `public/`（ビルド成果物の出力先）は環境変数化していない。計画書の Step 3 の領分と判断した。
  - `daily_news.yml` は無変更とした。Secrets の登録は Step 4 で Private 側に置く計画のため。
  - `source["url"]` を読むのは `collectors/rss.py` の1箇所だけなので、URLの解決は `normalize_source()` で行い、collector 側は変更しなかった。
- 未解決の課題:
  - **`scripts/fetch_rss.py` に同名関数の重複定義が3組ある。** Python はモジュール直下で後に書かれた定義が勝つため、前半の定義はどこからも到達しない。**前半を修正しても実行時の挙動は一切変わらない。** Step 1 の作業中、私自身も最初に無効な `fetch_source` を編集し、気づいて有効な方に付け直した。今後の修正が黙って無効化される危険がある。オーナーの判断で対応は保留（2026-09-09 時点）。

    | 関数 | 定義行 | 有効な定義 | 死んだ行数 |
    | --- | --- | --- | --- |
    | `ai_translate_and_summarize` | 326 / 1007 | 1007 | 80 |
    | `normalize_entry` | 408 / 1068 | 1068 | 31 |
    | `fetch_source` | 441 / 1225 | 1225 | 13 |

    合計124行。行番号は main `cb5c25c` 時点。

    3組とも中身が異なり、単なる重複ではない。前半は後半に置き換えられた**古い版**で、置換ではなく追記されたまま残ったものと見られる。たとえば `ai_translate_and_summarize` は、前半がAPIキー有無の分岐を持つ旧シグネチャ（4値タプルを返す）、後半が Haiku 一括翻訳を受け取る新シグネチャ（5値タプルを返す）である。`normalize_entry` も同様に、後半だけが `haiku_translations` 引数を持つ。

    削除の安全性について確認した事実:
    - 前半の定義を呼ぶモジュール直下のコードは存在しない（定義の間に実行される呼び出しが無いため、削除で束縛先が変わる箇所は無い）。
    - 呼び出しは関数内からのみで、実行時にはすべて後半の定義に束縛される。
    - 外部からの参照は `tests/test_regressions.py` の `fetch_rss.fetch_source` 1箇所のみで、これも後半の定義を見ている。

    以上より削除は挙動を変えない見込みだが、124行の削除であり、別PRで扱うのが妥当と考える。
- 次のアクション:
  1. 計画書の Step 2（`themes/example/`）に着手する。
  2. `fetch_rss.py` の重複定義の扱いを判断する。
  3. `Daily Personal Newsroom` を main で手動実行し、Step 1 のログ出力を実機で確認する。

### 2026-09-09 - Claude

- 目的: 設定層の分離計画を、次のエージェントが会話履歴なしで着手できる形で残す。
- 背景: `project-dashboard` 側の公開戦略の検討で、本リポジトリの `config/` が「実装の付属物」ではなく「将来の製品そのもの（テーマパック）」であると整理された。Google アラートURLの露出は、その構造が未分離であることの症状として位置づけ直した。
- 完了した作業:
  - `docs/config-separation-plan.md` を追加。
  - `WORKLOG.md` の Current handoff を、当該計画へ引き継げる内容に書き換えた。
- 影響範囲: `docs/config-separation-plan.md`、`WORKLOG.md`。コード変更なし。
- 検証: ドキュメントのみのため、テスト・ビルドへの影響はない。`config/sources.yaml` から `source_type: "google_alert"` の5件を機械的に抽出し、計画内の一覧が実データと一致することを確認した（food 2件・ai_dev 1件・egg 2件）。
- 決定:
  - **本リポジトリは Public のままとする。** 当初は Private 化を検討したが、外部へ見せる対象はエンジンであり、公開されていること自体に価値があると整理した。隠すのは設定層のみ。
  - **リポジトリ名と配信URLを変えない。** 本リポジトリが Public なのは GitHub Pages で配信するためであり、オーナーは毎日スマホでこのサイトを読んでいる。ホーム画面のショートカットを維持することを設計制約に置いた。
  - **git 履歴の書き換えは行わない。** 既に公開済みであり、効果に対してリスクが見合わない。露出済みURLはアラートの作り直しで無効化する。
- 未解決の課題:
  - 露出中の Google アラートURLは、Step 7 を実施するまで有効なまま。
  - テーマパックの販売形態が未決。
  - LICENSE ファイルが未整備。
- 次のアクション: 上記 Current handoff を参照。

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
