from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_PATH = ROOT / "data" / "articles.json"
FEEDBACK_PATH = ROOT / "data" / "feedback.json"
PREFERENCES_PATH = ROOT / "config" / "preferences.yaml"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9_+#.-]+|[\u3040-\u30ff\u3400-\u9fff]+", text.lower())
    return {word for word in words if len(word) >= 2}


def recency_score(published_at: str) -> float:
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.4
    age_hours = max(0.0, (datetime.now(timezone.utc) - published).total_seconds() / 3600)
    return max(0.0, math.exp(-age_hours / 96))


def feedback_score(article: dict, feedback_items: list[dict]) -> float:
    if not feedback_items:
        return 0.0
    article_tokens = tokenize(" ".join((article.get("title", ""), article.get("original_title", ""), article.get("raw_summary", ""))))
    score = 0.0
    for item in feedback_items:
        direction = 1 if item.get("value") == "like" else -1
        source_match = 1.0 if item.get("source") == article.get("source") else 0.0
        item_tokens = set(item.get("keywords", [])) or tokenize(item.get("title", ""))
        overlap = len(article_tokens & item_tokens) / max(1, len(article_tokens | item_tokens))
        score += direction * ((0.65 * overlap) + (0.35 * source_match))
    return max(-1.0, min(1.0, score))


def score_article(article: dict, prefs: dict, feedback: dict) -> float:
    category = article["category"]
    category_prefs = prefs["categories"].get(category, {})
    weights = prefs["scoring"]
    text = " ".join((article.get("title", ""), article.get("original_title", ""), article.get("raw_summary", ""))).lower()

    boost_keywords = category_prefs.get("boost_keywords", [])
    downrank_keywords = category_prefs.get("downrank_keywords", [])
    boost_hits = sum(1 for kw in boost_keywords if kw.lower() in text)
    down_hits = sum(1 for kw in downrank_keywords if kw.lower() in text)
    keyword = max(0.0, min(1.0, (boost_hits - (0.5 * down_hits)) / max(3, len(boost_keywords) / 3)))

    preferred = prefs.get("preferred_sources", {}).get(category, [])
    source = 1.0 if article.get("source") in preferred else 0.45
    recency = recency_score(article.get("published_at", ""))
    learned = (feedback_score(article, feedback.get(category, [])) + 1) / 2

    egg_price_penalty = 0.0
    if category == "egg" and any(kw in text for kw in ("關難ｽ｡隴ｬ・ｼ", "騾ｶ・ｸ陜｣・ｴ", "陷奇ｽｵ關難ｽ｡", "price")):
        egg_price_penalty = weights.get("egg_price_weight", 0.05)

    score = (
        weights["keyword_weight"] * keyword
        + weights["source_weight"] * source
        + weights["recency_weight"] * recency
        + weights["feedback_weight"] * learned
        - egg_price_penalty
    )
    return round(max(0, min(100, score * 100)), 1)


def enforce_category_limits(articles: list[dict], per_category: int = 10) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        grouped.setdefault(article["category"], []).append(article)

    selected = []
    for category, items in grouped.items():
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        if category == "egg":
            domestic = [x for x in items if x.get("source_region") != "global"]
            global_items = [x for x in items if x.get("source_region") == "global"]
            egg_selection = domestic[:8] + global_items[:2]
            selected_ids = {x["id"] for x in egg_selection}
            for item in items:
                if len(egg_selection) >= per_category:
                    break
                if item["id"] not in selected_ids:
                    egg_selection.append(item)
                    selected_ids.add(item["id"])
            selected.extend(egg_selection[:per_category])
        else:
            selected.extend(items[:per_category])
    unique = []
    seen = set()
    for article in selected:
        seen_key = f"{article['category']}:{article['id']}"
        if seen_key in seen:
            continue
        seen.add(seen_key)
        unique.append(article)
    return unique


def main() -> None:
    articles = load_json(ARTICLES_PATH, [])
    prefs = load_yaml(PREFERENCES_PATH)
    feedback = load_json(FEEDBACK_PATH, {})
    for article in articles:
        article["score"] = score_article(article, prefs, feedback)
    articles = enforce_category_limits(articles, 10)
    ARTICLES_PATH.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Scored {len(articles)} articles")


if __name__ == "__main__":
    main()
