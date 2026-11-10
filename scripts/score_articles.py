from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from newsroom_config import category_keys, category_profile, category_settings, config_path, state_path
from newsroom_logging import get_logger


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_PATH = state_path("articles.json")
FEEDBACK_PATH = state_path("feedback.json")
PREFERENCES_PATH = config_path("preferences.yaml")
LOG = get_logger()
RULES_PATH = config_path("rules.yaml")
CROSS_CATEGORY_DUPLICATE_KEY_FIELDS = ("url", "original_title", "title")

# Category-specific keyword lists live in the theme pack's rules.yaml
# (category_rules.<category>.<list>), not in the engine. Each module-level
# name below is bound from that file; a missing file or list leaves it empty.
# The formulas that use them stay here until categories themselves become
# configurable (#44).
CATEGORY_RULE_NAMES = {
    "EGG_REQUIRED_KEYWORDS": ("egg", "required"),
    "EGG_WEAK_CONTEXT_KEYWORDS": ("egg", "weak_context"),
    "FOOD_PRODUCT_DEV_KEYWORDS": ("egg", "product_dev"),
    "FOOD_PRODUCT_DEV_CONTEXT_KEYWORDS": ("egg", "product_dev_context"),
    "EGG_OFF_TOPIC_KEYWORDS": ("egg", "off_topic"),
    "RELEASE_ONLY_KEYWORDS": ("egg", "release_only"),
    "EGG_TECH_DEV_KEYWORDS": ("egg", "tech_dev"),
    "EGG_SWEETS_ONLY_DOWNRANK_KEYWORDS": ("egg", "sweets_only_downrank"),
    "EGG_CONSUMER_ONLY_DOWNRANK_KEYWORDS": ("egg", "consumer_only_downrank"),
    "EGG_PRICE_KEYWORDS": ("egg", "price"),
    "AI_TECH_BOOST_KEYWORDS": ("ai_dev", "tech_boost"),
    "AI_COMMERCE_DOWNRANK_KEYWORDS": ("ai_dev", "commerce_downrank"),
    "FOOD_TREND_KEYWORDS": ("food", "trend"),
    "FOOD_DEV_DOWNRANK_KEYWORDS": ("food", "dev_downrank"),
}
# Lists that make up the egg relevance filter. With none of them configured
# the filter is off and every egg article counts as relevant.
EGG_RELEVANCE_RULES = (
    "EGG_REQUIRED_KEYWORDS",
    "EGG_WEAK_CONTEXT_KEYWORDS",
    "FOOD_PRODUCT_DEV_KEYWORDS",
    "FOOD_PRODUCT_DEV_CONTEXT_KEYWORDS",
    "EGG_TECH_DEV_KEYWORDS",
)


def apply_category_rules(rules: dict | None) -> None:
    """Bind the keyword lists from a parsed rules.yaml (or clear them with None)."""
    categories = (rules or {}).get("category_rules") or {}
    for name, (category, key) in CATEGORY_RULE_NAMES.items():
        values = (categories.get(category) or {}).get(key) or []
        globals()[name] = tuple(str(value) for value in values)


def load_category_rules(path: Path | None = None) -> None:
    path = path or RULES_PATH
    if not path.exists():
        LOG.info(f"[rules] {path.name} not found; category keyword rules are empty")
        apply_category_rules(None)
        return
    with path.open("r", encoding="utf-8") as f:
        apply_category_rules(yaml.safe_load(f))


def egg_relevance_rules_configured() -> bool:
    return any(globals()[name] for name in EGG_RELEVANCE_RULES)


load_category_rules()


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
        if item.get("value") not in {"like", "bad"}:
            continue
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
    profile = category_profile(article.get("category"))
    text = article_text(article)
    if profile == "ai_dev":
        tech_hits = keyword_hits(text, AI_TECH_BOOST_KEYWORDS)
        commerce_hits = keyword_hits(text, AI_COMMERCE_DOWNRANK_KEYWORDS)
        adjustment = min(0.18, tech_hits * 0.035) - min(0.36, commerce_hits * 0.09)
        if commerce_hits and tech_hits == 0:
            adjustment -= 0.12
        elif commerce_hits >= 2:
            adjustment -= 0.08
        return adjustment
    if profile == "food":
        trend_hits = keyword_hits(text, FOOD_TREND_KEYWORDS)
        dev_hits = keyword_hits(text, FOOD_DEV_DOWNRANK_KEYWORDS)
        return min(0.12, trend_hits * 0.025) - min(0.12, dev_hits * 0.035)
    if profile == "egg":
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
    if not egg_relevance_rules_configured():
        return 1.0
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

    profile = category_profile(category)
    egg_price_penalty = 0.0
    egg_relevance = 1.0
    article["category_relevance"] = 1.0
    if profile == "egg" and any(kw in text for kw in EGG_PRICE_KEYWORDS):
        egg_price_penalty = weights.get("egg_price_weight", 0.05)
    if profile == "egg":
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
    if profile == "egg":
        score *= egg_relevance
    score_value = round(max(0, min(100, score * 100)), 1)
    if article.get("source_type") == "fallback":
        score_value = min(score_value, 25.0)
    return score_value


def source_limit_for_category(category: str) -> int | None:
    limit = category_settings(category)["source_limit"]
    return int(limit) if limit else None


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
    for category in category_keys():
        LOG.info(f"[display_summary] {category}: displayed={display_counts.get(category, 0)}")
    LOG.info("=== Personal Newsroom Score Summary ===")
    for category in category_keys():
        LOG.info(
            f"{category}: input={input_counts.get(category, 0)}, "
            f"displayed={display_counts.get(category, 0)}, "
            f"fallback={fallback_counts.get(category, 0)}"
        )
    ARTICLES_PATH.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.info(f"Scored {len(articles)} articles")


if __name__ == "__main__":
    main()
