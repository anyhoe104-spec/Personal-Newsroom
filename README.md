# Personal-Newsroom

自分専用のスマホ向けニュースMVPです。カテゴリ別RSSを取得し、要約、スコアリング、カテゴリ別10件表示、いいね / バッドのフィードバックUIを提供します。

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

## GitHub Pages

Pagesの公開元をGitHub Actionsに設定してください。`daily_news.yml` が毎日 `public/` を生成し、Pages artifactとしてアップロードします。

## ファイル構成

- `config/sources.yaml`: RSSソース
- `config/preferences.yaml`: スコアリング設定とカテゴリ別キーワード
- `config/prompts.yaml`: AI要約用プロンプト
- `scripts/fetch_rss.py`: RSS取得と要約
- `scripts/score_articles.py`: スコアリングとカテゴリ10件への絞り込み
- `scripts/build_site.py`: 静的HTML生成
- `scripts/update_preferences.py`: `feedback.json` から好み設定を更新
- `public/index.html`: GitHub Pages用HTML
- `public/style.css`: スマホ優先CSS
- `public/app.js`: タブ表示とフィードバックUI
- `data/articles.json`: 記事データ
- `data/feedback.json`: 次回スコア反映用フィードバック
