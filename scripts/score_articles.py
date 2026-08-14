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
AI_TECH_BOOST_KEYWORDS = (
    "ai agent",
    "agentic",
    "llm",
    "rag",
    "api",
    "sdk",
    "codex",
    "claude code",
    "github copilot",
    "openai",
    "anthropic",
    "gemini",
    "model",
    "inference",
    "eval",
    "benchmark",
    "developer",
    "workflow",
    "automation",
    "security",
    "observability",
    "オープンソース",
    "推論",
    "評価",
    "開発者",
    "自動化",
    "生成ai",
    "aiエージェント",
    "モデル",
)
AI_COMMERCE_DOWNRANK_KEYWORDS = (
    "sale",
    "summer sale",
    "kindle",
    "campaign",
    "coupon",
    "discount",
    "price",
    "new product",
    "book",
    "books",
    "発売",
    "新商品",
    "セール",
    "割引",
    "キャンペーン",
    "クーポン",
    "価格",
    "最大",
    "書籍",
    "本",
    "円",
    "off",
)
FOOD_TREND_KEYWORDS = (
    "スイーツ",
    "カフェ",
    "レストラン",
    "新商品",
    "期間限定",
    "発売",
    "メニュー",
    "dessert",
    "restaurant",
    "bakery",
    "cafe",
)
FOOD_DEV_DOWNRANK_KEYWORDS = (
    "商品開発",
    "共同開発",
    "加工技術",
    "製法",
    "原料",
    "品質",
    "工場",
    "研究",
    "food tech",
    "formulation",
)
EGG_TECH_DEV_KEYWORDS = (
    "卵",
    "たまご",
    "玉子",
    "商品開発",
    "技術開発",
    "共同開発",
    "加工技術",
    "製法",
    "原料",
    "品質",
    "工場",
    "研究",
    "新規事業",
    "海外展開",
    "代替卵",
    "卵加工",
    "液卵",
    "ゆで卵",
    "温泉卵",
    "加工卵",
    "plant-based",
    "formulation",
    "processing",
    "co-developed",
    "product development",
    "food",
    "food tech",
    "food technology",
    "manufacturing",
    "r&d",
    "research and development",
    "innovation",
    "ingredient",
    "ingredients",
    "supply chain",
    "automation",
    "plant",
    "protein",
    "cultivated",
    "cell-based",
    "fermentation",
    "packaging",
)
EGG_SWEETS_ONLY_DOWNRANK_KEYWORDS = (
    "スイーツ",
    "カフェ",
    "アイス",
    "ケーキ",
    "チョコ",
    "キャンペーン",
    "セール",
    "値引き",
    "dessert",
    "cafe",
    "ice cream",
)
EGG_CONSUMER_ONLY_DOWNRANK_KEYWORDS = (
    "レシピ",
    "作って",
    "食べ方",
    "ランチョンセミナー",
    "フェア",
    "ホテル",
    "駅",
    "開店",
    "ピザ",
    "ドーナツ",
    "アイス",
    "パン",
    "ワイン",
    "recipe",
)
CROSS_CATEGORY_DUPLICATE_KEY_FIELDS = ("url", "original_title", "title")


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


def keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword.lower() in text)


def normalized_duplicate_key(article: dict) -> str:
    for field in CROSS_CATEGORY_DUPLICATE_KEY_FIELDS:
        value = str(article.get(field, "")).strip().lower()
        if value:
            return re.sub(r"\s+", " ", value)
    return str(article.get("id", ""))


def category_quality_adjustment(article: dict) -> float:
    category = article.get("category")
    text = article_text(article)
    if category == "ai_dev":
        tech_hits = keyword_hits(text, AI_TECH_BOOST_KEYWORDS)
        commerce_hits = keyword_hits(text, AI_COMMERCE_DOWNRANK_KEYWORDS)
        adjustment = min(0.18, tech_hits * 0.035) - min(0.36, commerce_hits * 0.09)
        if commerce_hits and tech_hits == 0:
            adjustment -= 0.12
        elif commerce_hits >= 2:
            adjustment -= 0.08
        return adjustment
    if category == "food":
        trend_hits = keyword_hits(text, FOOD_TREND_KEYWORDS)
        dev_hits = keyword_hits(text, FOOD_DEV_DOWNRANK_KEYWORDS)
        return min(0.12, trend_hits * 0.025) - min(0.12, dev_hits * 0.035)
    if category == "egg":
        tech_hits = keyword_hits(text, EGG_TECH_DEV_KEYWORDS)
        sweets_hits = keyword_hits(text, EGG_SWEETS_ONLY_DOWNRANK_KEYWORDS)
        consumer_hits = keyword_hits(text, EGG_CONSUMER_ONLY_DOWNRANK_KEYWORDS)
        adjustment = min(0.24, tech_hits * 0.045) - min(0.26, sweets_hits * 0.07)
        if sweets_hits and tech_hits == 0:
            adjustment -= 0.16
        if consumer_hits and tech_hits <= 1:
            adjustment -= min(0.2, consumer_hits * 0.08)
        return adjustment
    return 0.0


def egg_article_relevance(article: dict) -> float:
    text = article_text(article)
    required_hits = sum(1 for kw in EGG_REQUIRED_KEYWORDS if kw.lower() in text)
    context_hits = sum(1 for kw in EGG_WEAK_CONTEXT_KEYWORDS if kw.lower() in text)
    product_dev_hits = sum(1 for kw in FOOD_PRODUCT_DEV_KEYWORDS if kw.lower() in text)
    product_context_hits = sum(1 for kw in FOOD_PRODUCT_DEV_CONTEXT_KEYWORDS if kw.lower() in text)
    off_topic_hits = sum(1 for kw in EGG_OFF_TOPIC_KEYWORDS if kw.lower() in text)
    release_only_hits = sum(1 for kw in RELEASE_ONLY_KEYWORDS if kw.lower() in text)
    readable_tech_hits = keyword_hits(text, EGG_TECH_DEV_KEYWORDS)
    consumer_only_hits = keyword_hits(text, EGG_CONSUMER_ONLY_DOWNRANK_KEYWORDS)
    sweets_only_hits = keyword_hits(text, EGG_SWEETS_ONLY_DOWNRANK_KEYWORDS)
    if consumer_only_hits and readable_tech_hits <= 2:
        return 0.25
    if sweets_only_hits and product_dev_hits == 0 and readable_tech_hits <= 1:
        return 0.25
    if required_hits:
        return max(
            0.2,
            min(
                1.0,
                0.65
                + (0.12 * required_hits)
                + (0.06 * context_hits)
                + (0.06 * readable_tech_hits)
                - (0.1 * off_topic_hits)
                - (0.08 * consumer_only_hits),
            ),
        )
    if readable_tech_hits >= 2 and consumer_only_hits == 0:
        return max(0.52, min(0.9, 0.48 + (0.08 * readable_tech_hits) + (0.03 * product_context_hits)))
    if readable_tech_hits >= 1 and product_dev_hits >= 1 and consumer_only_hits == 0:
        return 0.5
    if context_hits >= 2 and off_topic_hits == 0:
        return 0.45
    if product_dev_hits >= 2:
        return max(0.35, min(0.85, 0.42 + (0.08 * product_dev_hits) + (0.04 * product_context_hits) - (0.1 * release_only_hits)))
    if product_dev_hits >= 1 and product_context_hits >= 2 and release_only_hits == 0:
        return 0.48
    return 0.0


def egg_article_is_relevant(article: dict) -> bool:
    # Keep borderline food-development articles when egg-specific coverage is thin.
    # Scores below 0.45 remain too broad or consumer-oriented for this category.
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
    category_adjustment = category_quality_adjustment(article)
    article["category_quality_adjustment"] = round(category_adjustment, 3)

    score = (
        weights["keyword_weight"] * keyword
        + weights["source_weight"] * source
        + weights["recency_weight"] * recency
        + weights["feedback_weight"] * learned
        + category_adjustment
        - egg_price_penalty
    )
    if category == "egg":
        score *= egg_relevance
    score_value = round(max(0, min(100, score * 100)), 1)
    if article.get("source_type") == "fallback":
        score_value = min(score_value, 25.0)
    return score_value


def source_limit_for_category(category: str) -> int | None:
    if category == "ai_dev":
        return 4
    if category == "egg":
        return 5
    if category == "food":
        return 6
    return None


def select_category_articles(
    category: str,
    items: list[dict],
    per_category: int,
    used_duplicate_keys: set[str],
) -> list[dict]:
    selected: list[dict] = []
    selected_ids: set[str] = set()
    source_counts: dict[str, int] = {}
    source_limit = source_limit_for_category(category)

    def can_add(item: dict, enforce_source_limit: bool) -> bool:
        duplicate_key = normalized_duplicate_key(item)
        if duplicate_key in used_duplicate_keys or item["id"] in selected_ids:
            return False
        if enforce_source_limit and source_limit is not None:
            source = str(item.get("source", "unknown"))
            if source_counts.get(source, 0) >= source_limit:
                return False
        return True

    for enforce_source_limit in (True, False):
        for item in items:
            if len(selected) >= per_category:
                break
            if not can_add(item, enforce_source_limit):
                continue
            selected.append(item)
            selected_ids.add(item["id"])
            used_duplicate_keys.add(normalized_duplicate_key(item))
            source = str(item.get("source", "unknown"))
            source_counts[source] = source_counts.get(source, 0) + 1
    return selected


def enforce_category_limits(articles: list[dict], per_category: int = 10) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        grouped.setdefault(article["category"], []).append(article)

    selected = []
    used_duplicate_keys: set[str] = set()
    category_order = ["business", "ai_dev", "egg", "food"]
    category_order.extend(category for category in grouped if category not in category_order)
    for category in category_order:
        items = grouped.get(category, [])
        if not items:
            continue
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        selected.extend(select_category_articles(category, items, per_category, used_duplicate_keys))
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
