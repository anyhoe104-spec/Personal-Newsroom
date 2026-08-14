import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_rss  # noqa: E402
import score_articles  # noqa: E402
import validate_newsroom  # noqa: E402


def article(article_id: str, category: str, **overrides) -> dict:
    item = {
        "id": article_id,
        "category": category,
        "title": f"Article {article_id}",
        "original_title": "",
        "raw_summary": "",
        "source": "source-a",
        "source_type": "rss",
        "score": 50,
        "url": f"https://example.com/{article_id}",
    }
    item.update(overrides)
    return item


class ScoringRegressionTests(unittest.TestCase):
    def test_ai_technical_article_outranks_commerce_article(self):
        technical = article(
            "technical",
            "ai_dev",
            title="LLM agent API evaluation workflow for developers",
        )
        commerce = article(
            "commerce",
            "ai_dev",
            title="Kindle book sale coupon campaign",
        )

        self.assertGreater(
            score_articles.category_quality_adjustment(technical),
            score_articles.category_quality_adjustment(commerce),
        )

    def test_fallback_score_is_capped(self):
        fallback = article("fallback", "business", source_type="fallback")
        prefs = {
            "categories": {"business": {"boost_keywords": [], "downrank_keywords": []}},
            "preferred_sources": {"business": ["source-a"]},
            "scoring": {
                "keyword_weight": 0.0,
                "source_weight": 1.0,
                "recency_weight": 0.0,
                "feedback_weight": 0.0,
            },
        }

        self.assertEqual(score_articles.score_article(fallback, prefs, {}), 25.0)

    def test_ai_source_limit_applies_when_alternatives_exist(self):
        items = [article(f"a-{i}", "ai_dev", source="source-a", score=100 - i) for i in range(6)]
        items.extend(
            article(f"b-{i}", "ai_dev", source=f"source-{i}", score=80 - i)
            for i in range(6)
        )

        selected = score_articles.select_category_articles("ai_dev", items, 10, set())

        self.assertEqual(len(selected), 10)
        self.assertLessEqual(sum(item["source"] == "source-a" for item in selected), 4)

    def test_cross_category_duplicate_is_suppressed(self):
        shared_url = "https://example.com/shared"
        items = [
            article("business-1", "business", url=shared_url, score=90),
            article("ai-1", "ai_dev", url=shared_url, score=95),
            article("ai-2", "ai_dev", score=80),
        ]

        selected = score_articles.enforce_category_limits(items, per_category=2)

        self.assertEqual(sum(item["url"] == shared_url for item in selected), 1)
        self.assertIn("business-1", {item["id"] for item in selected})

    def test_borderline_egg_development_article_is_kept(self):
        item = article(
            "egg-borderline",
            "egg",
            title="食品工場の製造技術と品質管理",
            raw_summary="食品産業の加工技術と製造工程を解説する",
        )

        self.assertGreaterEqual(score_articles.egg_article_relevance(item), 0.45)
        self.assertTrue(score_articles.egg_article_is_relevant(item))


class TranslationRegressionTests(unittest.TestCase):
    def test_specific_japanese_translation_is_usable(self):
        item = {
            "original_title": "OpenAI launches a new Codex workflow",
            "translated_title": "OpenAIが新しいCodexワークフローを公開",
            "translated_summary": [
                "OpenAIが開発作業向けの新機能を公開した",
                "Codexによる実装と確認の流れを効率化する",
                "開発チームの反復作業を短縮できる",
            ],
            "impact": "ニュース収集基盤の開発手順を自動化する際の参考になる。",
        }

        self.assertTrue(fetch_rss.usable_ai_dev_translation(item))

    def test_generic_translation_title_is_rejected(self):
        item = {
            "original_title": "OpenAI launches a new Codex workflow",
            "translated_title": "AI・開発ニュースの注目アップデート",
            "translated_summary": ["要点その一", "要点その二", "要点その三"],
            "impact": "開発作業の具体的な自動化方法を検討する材料になる。",
        }

        self.assertFalse(fetch_rss.usable_ai_dev_translation(item))

    def test_english_summary_is_rejected(self):
        self.assertTrue(
            fetch_rss.looks_like_untranslated_summary(
                ["This is an English summary", "Developer workflow update", "Read the article"]
            )
        )

    def test_japanese_display_article_gets_localized_fields(self):
        item = article(
            "jp-1",
            "ai_dev",
            title="生成AIを使った開発ワークフローの改善",
            original_title="生成AIを使った開発ワークフローの改善",
            raw_summary="開発チームが生成AIを導入した事例を紹介します。",
            translated_title="",
            translated_summary=[],
            summary=[],
            impact="",
        )

        count = fetch_rss.ensure_ai_dev_japanese_display_articles_localized([item])

        self.assertEqual(count, 1)
        self.assertEqual(item["translated_title"], item["original_title"])
        self.assertEqual(len(item["translated_summary"]), 3)
        self.assertTrue(item["impact"])


class QualityMetricsRegressionTests(unittest.TestCase):
    def test_quality_metrics_report_real_rate_and_source_concentration(self):
        items = [
            article("real-1", "egg", source="source-a"),
            article("real-2", "egg", source="source-a"),
            article("fallback", "egg", source="sample", source_type="fallback"),
        ]

        metrics = validate_newsroom.category_quality_metrics(items, "egg")

        self.assertEqual(metrics["real_articles"], 2)
        self.assertAlmostEqual(metrics["real_article_rate"], 2 / 3)
        self.assertEqual(metrics["synthetic_fallback"], 1)
        self.assertEqual(metrics["localization_fallback"], 0)
        self.assertEqual(metrics["unique_sources"], 1)
        self.assertEqual(metrics["max_source_share"], 1.0)

    def test_translation_fallback_remains_a_real_article(self):
        item = article(
            "ai-real",
            "ai_dev",
            fallback_title="翻訳未取得: Original title",
        )

        metrics = validate_newsroom.category_quality_metrics([item], "ai_dev")

        self.assertEqual(metrics["real_articles"], 1)
        self.assertEqual(metrics["synthetic_fallback"], 0)
        self.assertEqual(metrics["localization_fallback"], 1)

    def test_cross_category_duplicate_metric(self):
        shared_url = "https://example.com/shared"
        items = [
            article("business", "business", url=shared_url),
            article("ai", "ai_dev", url=shared_url),
            article("egg", "egg"),
        ]

        self.assertEqual(validate_newsroom.cross_category_duplicate_count(items), 1)


if __name__ == "__main__":
    unittest.main()
