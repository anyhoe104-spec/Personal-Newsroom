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
EGG_REQUIRED_KEYWORDS = (
    "卵",
    "たまご",
    "玉子",
    "鶏卵",
    "ゆで卵",
    "ゆで玉子",
    "温泉卵",
    "煮卵",
    "半熟卵",
    "卵加工",
    "液卵",
    "厚焼",
    "オムライス",
    "egg",
    "eggs",
    "boiled egg",
    "egg product",
)
EGG_WEAK_CONTEXT_KEYWORDS = (
    "食品工場",
    "商品開発",
    "加工技術",
    "業務用",
    "惣菜",
    "製造",
    "品質",
)
FOOD_PRODUCT_DEV_KEYWORDS = (
    "商品開発",
    "共同開発",
    "開発",
    "コラボ",
    "コラボレーション",
    "企画",
    "開発背景",
    "開発秘話",
    "開発ストーリー",
    "開発エピソード",
    "ブランド戦略",
    "リブランディング",
    "素材",
    "製法",
    "技術",
    "品質",
    "食感",
    "味づくり",
    "味作り",
    "差別化",
    "リニューアル",
    "監修",
    "限定商品",
    "新ブランド",
    "新業態",
    "メーカー",
    "食品メーカー",
    "外食チェーン",
    "コンビニ",
    "小売",
    "惣菜",
    "冷凍食品",
    "チルド",
    "業務用",
    "plant-based",
    "collaboration",
    "co-developed",
    "product development",
    "formulation",
)
FOOD_PRODUCT_DEV_CONTEXT_KEYWORDS = (
    "発売",
    "新商品",
    "新メニュー",
    "期間限定",
    "リニューアル",
    "ブランド",
    "シリーズ",
    "ラインアップ",
    "店舗",
    "市場",
    "需要",
    "ターゲット",
)
EGG_OFF_TOPIC_KEYWORDS = (
    "スイーツ",
    "カフェ",
    "タルト",
    "メロン",
    "コーラ",
    "シェイク",
    "フラペチーノ",
    "ドリンク",
    "飲料",
    "キャンペーン",
    "クーポン",
    "値引き",
    "アイス",
)
RELEASE_ONLY_KEYWORDS = (
    "キャンペーン",
    "クーポン",
    "半額",
    "値引き",
    "お得",
    "セール",
    "福袋",
    "まとめ",
)


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


def article_text(article: dict) -> str:
    return " ".join(
        (
            str(article.get("title", "")),
            str(article.get("original_title", "")),
            str(article.get("raw_summary", "")),
        )
    ).lower()


def egg_article_relevance(article: dict) -> float:
    text = article_text(article)
    required_hits = sum(1 for kw in EGG_REQUIRED_KEYWORDS if kw.lower() in text)
    context_hits = sum(1 for kw in EGG_WEAK_CONTEXT_KEYWORDS if kw.lower() in text)
    product_dev_hits = sum(1 for kw in FOOD_PRODUCT_DEV_KEYWORDS if kw.lower() in text)
    product_context_hits = sum(1 for kw in FOOD_PRODUCT_DEV_CONTEXT_KEYWORDS if kw.lower() in text)
    off_topic_hits = sum(1 for kw in EGG_OFF_TOPIC_KEYWORDS if kw.lower() in text)
    release_only_hits = sum(1 for kw in RELEASE_ONLY_KEYWORDS if kw.lower() in text)
    if required_hits:
        return max(0.2, min(1.0, 0.65 + (0.12 * required_hits) + (0.06 * context_hits) - (0.1 * off_topic_hits)))
    if context_hits >= 2 and off_topic_hits == 0:
        return 0.45
    if product_dev_hits >= 2:
        return max(0.35, min(0.85, 0.42 + (0.08 * product_dev_hits) + (0.04 * product_context_hits) - (0.1 * release_only_hits)))
    if product_dev_hits >= 1 and product_context_hits >= 2 and release_only_hits == 0:
        return 0.48
    return 0.0


def egg_article_is_relevant(article: dict) -> bool:
    return egg_article_relevance(article) >= 0.45


def score_article(article: dict, prefs: dict, feedback: dict) -> float:
    category = article["category"]
    category_prefs = prefs["categories"].get(category, {})
    weights = prefs["scoring"]
    text = article_text(article)

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
    egg_relevance = 1.0
    article["category_relevance"] = 1.0
    if category == "egg" and any(kw in text for kw in ("關難ｽ｡隴ｬ・ｼ", "騾ｶ・ｸ陜｣・ｴ", "陷奇ｽｵ關難ｽ｡", "price")):
        egg_price_penalty = weights.get("egg_price_weight", 0.05)
    if category == "egg":
        egg_relevance = egg_article_relevance(article)
        article["category_relevance"] = egg_relevance

    score = (
        weights["keyword_weight"] * keyword
        + weights["source_weight"] * source
        + weights["recency_weight"] * recency
        + weights["feedback_weight"] * learned
        - egg_price_penalty
    )
    if category == "egg":
        score *= egg_relevance
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


def count_by_category(articles: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for article in articles:
        category = str(article.get("category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def fallback_count_by_category(articles: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for article in articles:
        if article.get("source_type") != "fallback" and not article.get("fallback_title"):
            continue
        category = str(article.get("category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def main() -> None:
    articles = load_json(ARTICLES_PATH, [])
    prefs = load_yaml(PREFERENCES_PATH)
    feedback = load_json(FEEDBACK_PATH, {})
    input_counts = count_by_category(articles)
    for article in articles:
        article["score"] = score_article(article, prefs, feedback)
    articles = enforce_category_limits(articles, 10)
    display_counts = count_by_category(articles)
    fallback_counts = fallback_count_by_category(articles)
    for category in ("business", "food", "ai_dev", "egg"):
        print(f"[display_summary] {category}: displayed={display_counts.get(category, 0)}")
    print("=== Personal Newsroom Score Summary ===")
    for category in ("business", "food", "ai_dev", "egg"):
        print(
            f"{category}: input={input_counts.get(category, 0)}, "
            f"scored={display_counts.get(category, 0)}, "
            f"displayed={display_counts.get(category, 0)}, "
            f"fallback={fallback_counts.get(category, 0)}"
        )
    ARTICLES_PATH.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Scored {len(articles)} articles")


if __name__ == "__main__":
    main()
