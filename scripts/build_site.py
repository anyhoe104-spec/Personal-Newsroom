from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_PATH = ROOT / "data" / "articles.json"
PUBLIC_DIR = ROOT / "public"
INDEX_PATH = PUBLIC_DIR / "index.html"


def load_articles() -> list[dict]:
    if not ARTICLES_PATH.exists():
        return []
    return json.loads(ARTICLES_PATH.read_text(encoding="utf-8"))


def main() -> None:
    articles = load_articles()
    category_order = ["business", "food", "ai_dev", "egg"]
    categories = {
        key: next((a["category_label"] for a in articles if a["category"] == key), key)
        for key in category_order
    }
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "categories": categories,
        "articles": articles,
    }
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Personal-Newsroom</title>
  <link rel="stylesheet" href="./style.css">
</head>
<body>
  <header class="app-header">
    <div>
      <p class="eyebrow">Personal-Newsroom</p>
      <h1>今日読むべき40本</h1>
    </div>
    <p class="updated">更新: <time id="generatedAt"></time></p>
  </header>

  <nav class="tabs" id="tabs" aria-label="カテゴリ"></nav>
  <main id="app" class="article-list"></main>

  <template id="articleTemplate">
    <article class="card">
      <div class="card-top">
        <span class="source"></span>
        <span class="score"></span>
      </div>
      <h2><a class="title" target="_blank" rel="noopener noreferrer"></a></h2>
      <p class="original-title"></p>
      <p class="category"></p>
      <ul class="summary"></ul>
      <p class="impact"></p>
      <p class="egg-insight"></p>
      <div class="actions">
        <button class="feedback like" type="button" data-value="like">いいね</button>
        <button class="feedback bad" type="button" data-value="bad">バッド</button>
      </div>
    </article>
  </template>

  <script id="newsData" type="application/json">{json.dumps(payload, ensure_ascii=False)}</script>
  <script src="./app.js"></script>
</body>
</html>
"""
    INDEX_PATH.write_text(html, encoding="utf-8")
    print(f"Built {INDEX_PATH}")


if __name__ == "__main__":
    main()
