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


def count_by_category(articles: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for article in articles:
        category = str(article.get("category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def translation_usable(article: dict) -> bool:
    if article.get("source_type") == "fallback" or article.get("fallback_title"):
        return False
    translated_summary = [line for line in article.get("translated_summary", []) if str(line).strip()]
    return bool(article.get("translated_title") and len(translated_summary) == 3 and article.get("impact"))


def main() -> None:
    articles = load_articles()
    display_counts = count_by_category(articles)
    for category in ("business", "food", "ai_dev", "egg"):
        print(f"[display_summary] {category}: displayed={display_counts.get(category, 0)}")
    translation_articles = [
        article
        for article in sorted(
            [article for article in articles if article.get("category") in {"ai_dev", "egg"}],
            key=lambda item: item.get("score", 0),
            reverse=True,
        )[:20]
    ]
    for article in translation_articles:
        print(
            {
                "build_article_id": article.get("id"),
                "category": article.get("category"),
                "translated_title_exists": bool(article.get("translated_title")),
                "translated_summary_exists": bool(article.get("translated_summary")),
                "impact_exists": bool(article.get("impact")),
                "translation_usable": translation_usable(article),
            }
        )
    translated_articles = sum(
        1
        for article in translation_articles
        if translation_usable(article)
    )
    print("=== Personal Newsroom Build Summary ===")
    for category in ("business", "food", "ai_dev", "egg"):
        print(f"{category}: displayed={display_counts.get(category, 0)}")
    print(
        "Translation render check: "
        f"final_display_translated_count={translated_articles}, "
        f"final_display_untranslated_count={len(translation_articles) - translated_articles}"
    )
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
  <section class="feedback-tools" aria-label="フィードバック管理">
    <button id="copyFeedback" type="button">フィードバックをコピー</button>
    <button id="downloadFeedback" type="button">JSON保存</button>
    <span id="feedbackStatus" aria-live="polite"></span>
  </section>
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
