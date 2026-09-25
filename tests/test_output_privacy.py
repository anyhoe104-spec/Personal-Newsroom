import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_source_feedback as analysis
import build_site


class OutputPrivacyTests(unittest.TestCase):
    def test_vocabulary_matches_public_text_in_its_own_category(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.yaml").write_text(
                "categories:\n  food:\n    boost_keywords: [Title, Translated, Raw, Summary, hidden, eggword]\n"
                "  egg:\n    boost_keywords: [eggword, hidden]\n", encoding="utf-8")
            (root / "learned.yaml").write_text(
                "categories:\n  food:\n    learned_tags: {learned: 2, private: 3}\n", encoding="utf-8")
            articles = [{"category": "food", "title": "TITLE", "translated_title": "translated",
                         "raw_summary": "raw", "summary": ["summary learned"],
                         "impact": "hidden private"},
                        {"category": "egg", "title": "eggword"}]
            with patch.dict(os.environ, {"NEWSROOM_CONFIG_DIR": str(root), "NEWSROOM_STATE_DIR": str(root)}):
                self.assertEqual(build_site.reader_vocabulary(articles), {
                    "food": ["Title", "Translated", "Raw", "Summary", "learned"], "egg": ["eggword"]})
                self.assertEqual(build_site.reader_vocabulary([]), {"food": [], "egg": []})

    def test_analysis_writes_only_state_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            with patch.object(analysis, "ARTICLES_PATH", state / "articles.json"), \
                 patch.object(analysis, "FEEDBACK_PATH", state / "feedback.json"), \
                 patch.object(analysis, "HISTORY_PATH", state / "run_history.json"), \
                 patch.object(analysis, "RECOMMENDATIONS_PATH", state / "source_recommendations.json"), \
                 patch.object(analysis, "write_json", wraps=analysis.write_json) as write:
                analysis.main()
            self.assertEqual([call.args[0] for call in write.call_args_list], [
                state / "run_history.json", state / "source_recommendations.json"])
            self.assertEqual(len(json.loads((state / "run_history.json").read_text())), 1)


if __name__ == "__main__":
    unittest.main()
