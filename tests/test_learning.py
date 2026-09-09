import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_preferences import learned_preferences
from score_articles import feedback_score


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
