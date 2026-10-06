import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_preferences import learned_preferences
from score_articles import feedback_score, enforce_category_limits


class LearningTests(unittest.TestCase):
    def test_repeated_runs_reversals_and_category_isolation(self):
        prefs = {"categories": {"egg": {"boost_keywords": ["卵"]}}}
        vote = {"id": "a", "at": "2026-09-01", "value": "like", "keywords": ["製造", "製造"], "source": "Source"}
        result = learned_preferences(copy.deepcopy(prefs), {"egg": [vote]})
        self.assertEqual(result["categories"]["egg"]["learned_tags"], {"製造": 1})
        self.assertEqual(result, learned_preferences(copy.deepcopy(result), {"egg": [vote]}))
        reverse = {**vote, "at": "2026-09-02", "value": "bad"}
        updated = learned_preferences(result, {"egg": [vote, reverse]})
        self.assertEqual(updated["categories"]["egg"]["learned_tags"], {"製造": -1})
        self.assertEqual(updated["categories"]["egg"]["boost_keywords"], ["卵"])
        self.assertEqual(updated["categories"]["food"]["learned_tags"], {})
        cleared = learned_preferences(updated, {"egg": [{**reverse, "value": "none"}]})
        self.assertEqual(cleared["categories"]["egg"]["learned_tags"], {})

    def test_retracted_vote_is_neutral_in_pipeline(self):
        article = {"title": "製造", "source": "Source"}
        self.assertEqual(feedback_score(article, [{"source": "Source", "value": "none"}]), 0)
        self.assertGreater(feedback_score(article, [{"source": "Source", "value": "like"}]), 0)
        self.assertLess(feedback_score(article, [{"source": "Source", "value": "bad"}]), 0)

    def test_business_diversifies_without_losing_articles_when_only_one_source_exists(self):
        def candidates(source, count, score):
            return [{"id": f"{source}-{i}", "category": "business", "source": source,
                     "title": f"{source} story {i}", "url": f"https://example.org/{source}/{i}",
                     "score": score-i} for i in range(count)]
        preferred = candidates("A", 12, 100)
        alternative = candidates("B", 8, 50)
        selected = enforce_category_limits(preferred + alternative)
        self.assertEqual(len(selected), 10)
        self.assertEqual(sum(a["source"] == "A" for a in selected), 6)
        self.assertEqual(len(enforce_category_limits(preferred)), 10)
