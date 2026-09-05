from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from newsroom_logging import get_logger


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_PATH = ROOT / "data" / "articles.json"
INDEX_PATH = ROOT / "public" / "index.html"
CATEGORY_ORDER = ("business", "food", "ai_dev", "egg")
LOG = get_logger()


def load_articles() -> list[dict]:
    if not ARTICLES_PATH.exists():
        raise FileNotFoundError(f"Missing {ARTICLES_PATH}")
    return json.loads(ARTICLES_PATH.read_text(encoding="utf-8"))


def count_by_category(articles: list[dict]) -> Counter:
    return Counter(str(article.get("category", "unknown")) for article in articles)


def fallback_count_by_category(articles: list[dict]) -> Counter:
    return Counter(
        str(article.get("category", "unknown"))
        for article in articles
        if article.get("source_type") == "fallback" or article.get("fallback_title")
    )


def translation_usable(article: dict, category: str) -> bool:
    if article.get("category") != category:
        return False
    if article.get("source_type") == "fallback" or article.get("fallback_title"):
        return False
    translated_summary = [line for line in article.get("translated_summary", []) if str(line).strip()]
    return bool(article.get("translated_title") and len(translated_summary) == 3 and article.get("impact"))


def ai_dev_translation_usable(article: dict) -> bool:
    return translation_usable(article, "ai_dev")


def category_quality_metrics(articles: list[dict], category: str) -> dict[str, float | int]:
    category_articles = [article for article in articles if article.get("category") == category]
    displayed = len(category_articles)
    synthetic_fallback = sum(1 for article in category_articles if article.get("source_type") == "fallback")
    localization_fallback = sum(
        1 for article in category_articles
        if article.get("source_type") != "fallback" and article.get("fallback_title")
    )
    real_articles = displayed - synthetic_fallback
    source_counts = Counter(
        str(article.get("source") or "unknown")
        for article in category_articles
        if article.get("source_type") != "fallback"
    )
    largest_source = max(source_counts.values(), default=0)
    return {
        "displayed": displayed,
        "real_articles": real_articles,
        "synthetic_fallback": synthetic_fallback,
        "localization_fallback": localization_fallback,
        "real_article_rate": real_articles / displayed if displayed else 0.0,
        "unique_sources": len(source_counts),
        "max_source_share": largest_source / real_articles if real_articles else 0.0,
    }


def cross_category_duplicate_count(articles: list[dict]) -> int:
    categories_by_key: dict[str, set[str]] = {}
    for article in articles:
        key = str(article.get("url") or article.get("original_title") or article.get("title") or "").strip().lower()
        if not key:
            continue
        categories_by_key.setdefault(key, set()).add(str(article.get("category") or "unknown"))
    return sum(1 for categories in categories_by_key.values() if len(categories) > 1)


def content_tokens(article: dict) -> set[str]:
    text = " ".join(
        str(article.get(field) or "")
        for field in ("original_title", "title", "raw_summary")
    ).lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9+#.-]+|[\u3040-\u30ff\u3400-\u9fff]{2,}", text)
    stop_words = {"https", "http", "www", "com", "html", "新商品", "発売", "登場", "限定"}
    return {token for token in tokens if token not in stop_words and len(token) >= 2}


def near_duplicate_pairs(articles: list[dict], category: str, threshold: float = 0.42) -> int:
    category_articles = [article for article in articles if article.get("category") == category]
    token_sets = [content_tokens(article) for article in category_articles]
    pairs = 0
    for left_index, left_tokens in enumerate(token_sets):
        if not left_tokens:
            continue
        for right_tokens in token_sets[left_index + 1 :]:
            if not right_tokens:
                continue
            similarity = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
            if similarity >= threshold:
                pairs += 1
    return pairs


def validate() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    articles = load_articles()
    category_counts = count_by_category(articles)
    fallback_counts = fallback_count_by_category(articles)

    if not INDEX_PATH.exists():
        errors.append(f"Missing {INDEX_PATH}")

    for category in CATEGORY_ORDER:
        displayed = category_counts.get(category, 0)
        fallback = fallback_counts.get(category, 0)
        LOG.info(f"[validation_summary] {category}: displayed={displayed}, fallback={fallback}")
        if displayed != 10:
            errors.append(f"{category} displayed={displayed}; expected 10")
        metrics = category_quality_metrics(articles, category)
        LOG.info(
            f"[quality_metrics] {category}: real_articles={metrics['real_articles']}, "
            f"real_article_rate={metrics['real_article_rate']:.0%}, "
            f"synthetic_fallback={metrics['synthetic_fallback']}, "
            f"localization_fallback={metrics['localization_fallback']}, "
            f"unique_sources={metrics['unique_sources']}, "
            f"max_source_share={metrics['max_source_share']:.0%}"
        )

    duplicate_count = cross_category_duplicate_count(articles)
    LOG.info(f"[quality_duplicates] cross_category_duplicates={duplicate_count}")
    if duplicate_count:
        warnings.append(f"カテゴリ横断の重複記事が{duplicate_count}件あります。")
    for category in CATEGORY_ORDER:
        near_duplicates = near_duplicate_pairs(articles, category)
        LOG.info(f"[quality_near_duplicates] {category}: near_duplicate_pairs={near_duplicates}")
        if category == "food" and near_duplicates >= 3:
            warnings.append("食品カテゴリで近い内容の記事が多めです。ソース構成または選別条件の見直し候補です。")

    ai_dev_articles = [article for article in articles if article.get("category") == "ai_dev"]
    translated_ai_dev = sum(1 for article in ai_dev_articles if ai_dev_translation_usable(article))
    LOG.info(
        "[validation_ai_dev] "
        f"usable_translations={translated_ai_dev}, untranslated={len(ai_dev_articles) - translated_ai_dev}, "
        f"translation_rate={translated_ai_dev / len(ai_dev_articles) if ai_dev_articles else 0:.0%}"
    )
    if ai_dev_articles and translated_ai_dev < 8:
        warnings.append(
            "AI・活用カテゴリの翻訳済み表示が8件未満です。APIキー未設定、API失敗、または汎用翻訳判定の可能性があります。"
        )

    egg_articles = [article for article in articles if article.get("category") == "egg"]
    translated_egg = sum(1 for article in egg_articles if translation_usable(article, "egg"))
    LOG.info(
        "[validation_egg_translation] "
        f"usable_translations={translated_egg}, untranslated={len(egg_articles) - translated_egg}, "
        f"translation_rate={translated_egg / len(egg_articles) if egg_articles else 0:.0%}"
    )
    egg_fallback = fallback_counts.get("egg", 0)
    strong_relevance = sum(
        1 for article in egg_articles
        if article.get("source_type") != "fallback" and float(article.get("category_relevance", 0)) >= 0.5
    )
    borderline_relevance = sum(
        1 for article in egg_articles
        if article.get("source_type") != "fallback" and 0.45 <= float(article.get("category_relevance", 0)) < 0.5
    )
    LOG.info(
        f"[validation_egg] real_articles={len(egg_articles) - egg_fallback}, fallback={egg_fallback}, "
        f"strong_relevance={strong_relevance}, borderline_relevance={borderline_relevance}"
    )
    if egg_articles and egg_fallback >= 8:
        warnings.append(
            "卵カテゴリのfallbackが8件以上です。現在のソースでは卵関連の実記事が不足している可能性があります。"
        )

    for warning in warnings:
        LOG.warning(f"[validation_warning] {warning}")
    for error in errors:
        LOG.error(f"[validation_error] {error}")

    if errors:
        LOG.error("Newsroom validation failed")
        return 1
    LOG.info("Newsroom validation passed")
    return 0


def main() -> None:
    sys.exit(validate())


if __name__ == "__main__":
    main()
