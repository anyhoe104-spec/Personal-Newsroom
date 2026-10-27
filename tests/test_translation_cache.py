import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_rss  # noqa: E402

TRANSLATION = {
    "translated_title": "企業が植物由来の卵商品を発売",
    "translated_summary": [
        "食品メーカーが植物由来の卵代替商品を発売した",
        "大豆由来タンパクの製造技術を用いている",
        "商品開発の参考になる動きである",
    ],
    "impact": "代替素材の動向として確認する価値がある。",
}


def egg_article():
    return {
        "id": "egg-article-1",
        "category": "egg",
        "category_label": "卵・食品開発",
        "title": "Company launches plant-based egg product",
        "original_title": "Company launches plant-based egg product",
        "raw_summary": "A food maker launched a plant-based egg product.",
        "translated_title": "",
        "translated_summary": [],
        "impact": "",
    }


def candidate(article):
    return {
        "stable_id": "egg_0",
        "id": article["id"],
        "category": "egg",
        "category_label": "卵・食品開発",
        "title": article["original_title"],
        "description": article["raw_summary"],
    }


class TranslationCacheTests(unittest.TestCase):
    """An article shown on several days keeps one translation (#49)."""

    def run_final(self, article, api):
        with mock.patch.object(fetch_rss, "select_final_translation_candidates", return_value=[candidate(article)]), \
                mock.patch.object(fetch_rss, "ensure_translation_japanese_display_articles_localized"), \
                mock.patch.object(fetch_rss, "log_final_ai_dev_display_status"), \
                mock.patch.object(fetch_rss, "call_anthropic_with_chunk_retry", api), \
                mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            fetch_rss.translate_final_ai_dev_articles([article])

    def test_second_day_reuses_the_first_translation_without_calling_the_api(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(fetch_rss, "TRANSLATION_CACHE_PATH", Path(directory) / "translation_cache.json"):
            first = egg_article()
            self.run_final(first, mock.Mock(return_value={"egg_0": dict(TRANSLATION)}))
            self.assertEqual(first["translated_title"], TRANSLATION["translated_title"])

            second = egg_article()
            api = mock.Mock(return_value={"egg_0": dict(TRANSLATION, translated_title="植物由来の卵代替品を企業が投入")})
            self.run_final(second, api)
            api.assert_not_called()
            self.assertEqual(second["translated_title"], first["translated_title"])
            self.assertEqual(second["translated_summary"], first["translated_summary"])
            self.assertEqual(fetch_rss.RUN_STATS["ai_translation"]["cache_hit_count"], 1)

    def test_cache_drops_entries_older_than_the_retention_window(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "translation_cache.json"
            now = datetime(2026, 10, 27, tzinfo=timezone.utc)
            old = (now - timedelta(days=fetch_rss.TRANSLATION_CACHE_DAYS + 1)).isoformat()
            fresh = (now - timedelta(days=1)).isoformat()
            fetch_rss.save_translation_cache({"old": {"cached_at": old}, "fresh": {"cached_at": fresh}}, path, now)
            self.assertEqual(set(fetch_rss.load_translation_cache(path)), {"fresh"})

    def test_unreadable_cache_starts_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "translation_cache.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(fetch_rss.load_translation_cache(path), {})


if __name__ == "__main__":
    unittest.main()
