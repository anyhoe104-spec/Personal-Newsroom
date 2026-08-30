# Personal-Newsroom

自分専用のスマホ向けニュースMVPです。カテゴリ別RSSを取得し、要約、スコアリング、カテゴリ別10件表示、いいね / バッドのフィードバックUIを提供します。

要件と現在の改修方針は [`docs/requirements.md`](docs/requirements.md) に整理しています。

## カテゴリ

- 経済・ビジネス
- スイーツ・飲食
- AI・開発
- 卵（加工品・ゆで卵・温泉卵・煮卵・商品開発・技術トレンド）

## ローカル実行手順（PowerShell）

Windows Terminal または PowerShell でリポジトリへ移動してから実行します。

```powershell
cd C:/Users/conve/Documents/Personal-Newsroom
python --version
python -m pip --version
python -m pip install -r requirements.txt
python scripts/fetch_rss.py
python scripts/score_articles.py
python scripts/build_site.py
```

回帰テストは次のコマンドで実行します。

```powershell
python -m unittest discover -s tests -v
```

生成後、`public/index.html` をブラウザで開くと確認できます。

`scripts/fetch_rss.py` はRSSごとの取得件数を表示します。取得できないRSSがあっても処理は続行し、カテゴリ内の記事が10件に満たない場合はfallback sampleを追加したカテゴリ名と不足件数をログに表示します。

## AI要約

APIキーなしでも動きます。その場合は記事タイトルとRSS概要から仮要約を生成します。

AI要約を使う場合は、どちらかを環境変数に設定してください。

```powershell
$env:OPENAI_API_KEY="..."
# または
$env:ANTHROPIC_API_KEY="..."
```

任意で `OPENAI_MODEL` または `ANTHROPIC_MODEL` も指定できます。

## フィードバック

ブラウザ上のいいね / バッドは、まず `localStorage` に保存されます。次回スコアに反映したい場合は、同じ形式の内容を `data/feedback.json` に反映してから以下を実行します。

```powershell
python scripts/update_preferences.py
python scripts/score_articles.py
python scripts/build_site.py
```

学習はカテゴリ内だけで行います。いいねは類似キーワードと同一ソースを上げ、バッドは下げます。

## GoogleアラートRSSの追加方法

Googleアラートで作成したアラートは、配信先をRSSにするとフィードURLを取得できます。取得したURLを `config/sources.yaml` の対象カテゴリに追加してください。

```yaml
categories:
  ai_dev:
    sources:
      - name: "Google Alert: AI agents"
        source_type: "google_alert"
        url: "https://www.google.com/alerts/feeds/xxxxxxxx/yyyyyyyy"
```

`source_type` は以下を想定しています。

- `rss`: 通常のRSSフィードです。既存RSS取得と同じ動作です。
- `google_alert`: GoogleアラートRSSです。通常RSSとして取得し、記事には `source_type: google_alert` を保存します。
- `api_stub`: 将来API取得を追加するための予約枠です。現時点では記事を追加せず、既存処理を止めません。

記事データには既存フィールドを残したまま、`source_type`、`original_title`、`translated_title` を追加します。AI・開発カテゴリでは、APIキーがある場合はOpenAIまたはAnthropicで日本語タイトル・要約を生成し、APIキーがない場合もフォールバックで日本語中心の要約を作ります。

## GitHub Pages

Pagesの公開元をGitHub Actionsに設定してください。`daily_news.yml` が毎日 `public/` を生成し、Pages artifactとしてアップロードします。

## ファイル構成

- `config/sources.yaml`: RSSソース
- `config/preferences.yaml`: スコアリング設定とカテゴリ別キーワード
- `config/prompts.yaml`: AI要約用プロンプト
- `scripts/fetch_rss.py`: RSS取得と要約
- `scripts/score_articles.py`: スコアリングとカテゴリ10件への絞り込み
- `scripts/build_site.py`: 静的HTML生成
- `scripts/validate_newsroom.py`: 生成結果の件数・fallback・AI翻訳状態チェック
- `scripts/update_preferences.py`: `feedback.json` から好み設定を更新
- `scripts/collectors/`: RSS、GoogleアラートRSS、将来API取得の入口
- `public/index.html`: GitHub Pages用HTML
- `public/style.css`: スマホ優先CSS
- `public/app.js`: タブ表示とフィードバックUI
- `data/articles.json`: 記事データ
- `data/feedback.json`: 次回スコア反映用フィードバック

## ログ設定

ログは Python 標準の `logging` に統一しています。出力形式は従来どおり `[タグ] 本文` のままです。

| 環境変数 | 既定値 | 説明 |
| --- | --- | --- |
| `NEWSROOM_LOG_LEVEL` | `INFO` | コンソール出力レベル。`DEBUG` にすると記事単位の翻訳診断ログが復活します（`LOG_LEVEL` でも可）。 |
| `NEWSROOM_LOG_FILE` | `logs/newsroom.log` | ログファイルの出力先。空文字を指定するとファイル出力を止めます。 |
| `NEWSROOM_LOG_FILE_LEVEL` | `DEBUG` | ファイル出力レベル。コンソールに出さない詳細もファイルには残ります。 |
| `NEWSROOM_LOG_MAX_BYTES` | `1048576`（1MiB） | 1ファイルあたりの上限。超えるとローテーションします。 |
| `NEWSROOM_LOG_BACKUP_COUNT` | `3` | 保持する世代数。上限に達した古いファイルから削除されます。 |

`logs/` は `.gitignore` 済みです。ローカル実行では最大 4MiB（1MiB × 4世代）でログの増加が止まります。

GitHub Actions は既定で `NEWSROOM_LOG_LEVEL=INFO`、ファイル出力なしで実行します。詳細を見たいときは `daily_news.yml` の `NEWSROOM_LOG_LEVEL` を `DEBUG` にして手動実行してください。

記事単位で繰り返し出るログには1実行あたりの件数上限があり、上限に達した場合は `[log_capped] グループ名: emitted=N, suppressed=M` を最後に出力します。ログが黙って欠けることはありません。

デバッグ時のみ出力されるログ（`NEWSROOM_LOG_LEVEL=DEBUG` が必要）:

- `[anthropic] request articles before prompt` / `request messages payload`
- `[anthropic] response content types` / `tool_use name` / `tool_use.input item`
- `[anthropic] translation_request_titles` / `translation_request_article_ids` / `final_ai_dev_display_article_ids`
- `[anthropic] ai_dev japanese passthrough` / `applied translation to article`
- 記事ごとの翻訳可否ダンプ（`article_id` / `translation_usable`）
- `[rss] 名称: parse warning`（feedparser の bozo 判定は誤検知が多いため）

## Actionsログの見方

GitHub Actions の `Fetch RSS`、`Score articles`、`Build site` のログを見ると、Daily Personal Newsroom の実行状態を確認できます。

RSS取得:

- `[rss_summary] category / source / source_type: fetched=N` は、そのRSSソースから記事を取得できたことを示します。
- `[rss_failure] category / source / source_type: reason` は、取得に失敗したソースです。
- `[rss_zero] category / source / source_type: 0 articles` は、接続はできたが記事が0件だったソースです。
- `=== Personal Newsroom Run Summary ===` のカテゴリ行で `fetched`、`displayed`、`fallback` を確認できます。

AI翻訳:

- `api_key_present=True` なら Anthropic API キーがActions環境にあります。キー値はログに出しません。
- `request_count=10` はAI・開発の最終表示候補10件を翻訳対象にしたことを示します。
- `source_japanese_count` はAI・開発の表示候補のうち、日本語原文としてClaude翻訳をスキップした件数です。
- `japanese_passthrough_count` は日本語原文記事に3点要約とimpactを補って表示可能にした件数です。
- `api_success=1`、`matched_count=10`、`meaningful_translation_count=10`、`fallback_count=0` なら翻訳は成功です。
- `request_display_match_count` で、翻訳対象と表示対象が一致しているか確認できます。内訳の `translation_request_article_ids` と `final_ai_dev_display_article_ids` は DEBUG レベルです（「ログ設定」を参照）。
- `final_display_translated_count` が8以上なら概ね成功です。10なら理想状態です。
- `fallback_count` が多い場合は、API失敗、レスポンス解析失敗、汎用翻訳判定、またはAPIキー未設定の可能性があります。

HTTPステータスの目安:

- `401`: 認証失敗。APIキーや権限を確認します。
- `402`: 支払い・クレジット不足の可能性があります。
- `403`: アクセス禁止。RSS側の拒否や権限不足です。
- `404`: URLまたはエンドポイントが見つかりません。
- `429`: レート制限です。時間を置くか上限を確認します。
- `504`: ゲートウェイタイムアウトです。外部サービス側の一時的な遅延の可能性があります。
- `529`: Anthropic の過負荷です。再試行で回復することがあります。

表示件数:

- `Score articles` と `Build site` の `[display_summary] category: displayed=10` を確認します。
- 4カテゴリすべてが `displayed=10` なら、UIに各カテゴリ10件を表示できます。

生成結果チェック:

- `Validate newsroom output` の `[validation_summary] category: displayed=10` を確認します。
- `[validation_warning]` はActionsを失敗させない注意ログです。卵カテゴリのfallback過多やAI翻訳不足を見ます。
- `[validation_error]` はActionsを失敗させる構造エラーです。カテゴリ件数不足や生成ファイル不足を見ます。
