from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_PATH = ROOT / "data" / "articles.json"
INDEX_PATH = ROOT / "public" / "index.html"
CATEGORY_ORDER = ("business", "food", "ai_dev", "egg")


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


def ai_dev_translation_usable(article: dict) -> bool:
    if article.get("category") != "ai_dev":
        return False
    if article.get("source_type") == "fallback" or article.get("fallback_title"):
        return False
    translated_summary = [line for line in article.get("translated_summary", []) if str(line).strip()]
    return bool(article.get("translated_title") and len(translated_summary) == 3 and article.get("impact"))


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
        print(f"[validation_summary] {category}: displayed={displayed}, fallback={fallback}")
        if displayed != 10:
            errors.append(f"{category} displayed={displayed}; expected 10")

    ai_dev_articles = [article for article in articles if article.get("category") == "ai_dev"]
    translated_ai_dev = sum(1 for article in ai_dev_articles if ai_dev_translation_usable(article))
    print(
        "[validation_ai_dev] "
        f"usable_translations={translated_ai_dev}, untranslated={len(ai_dev_articles) - translated_ai_dev}"
    )
    if ai_dev_articles and translated_ai_dev < 8:
        warnings.append(
            "AI・開発カテゴリの翻訳済み表示が8件未満です。APIキー未設定、API失敗、または汎用翻訳判定の可能性があります。"
        )

    egg_articles = [article for article in articles if article.get("category") == "egg"]
    egg_fallback = fallback_counts.get("egg", 0)
    print(f"[validation_egg] real_articles={len(egg_articles) - egg_fallback}, fallback={egg_fallback}")
    if egg_articles and egg_fallback >= 8:
        warnings.append(
            "卵カテゴリのfallbackが8件以上です。現在のソースでは卵関連の実記事が不足している可能性があります。"
        )

    for warning in warnings:
        print(f"[validation_warning] {warning}")
    for error in errors:
        print(f"[validation_error] {error}")

    if errors:
        print("Newsroom validation failed")
        return 1
    print("Newsroom validation passed")
    return 0


def main() -> None:
    sys.exit(validate())


if __name__ == "__main__":
    main()
