import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_site
import update_preferences
import yaml


class ReviewFixTests(unittest.TestCase):
    def test_cache_tracks_icons_and_code_but_not_daily_news(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = ("app.js", "learning.js", "i18n.js", "style.css", "pwa.js",
                      "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png")
            for name in assets:
                (root / name).write_bytes(name.encode())
            original = build_site.shell_digest(root)
            (root / "index.html").write_text("different daily articles")
            self.assertEqual(build_site.shell_digest(root), original)
            for name in assets:
                with self.subTest(asset=name):
                    (root / name).write_bytes(b"changed")
                    self.assertNotEqual(build_site.shell_digest(root), original)
                    (root / name).write_bytes(name.encode())

    def test_external_editorial_comments_survive_learning_and_retraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, state = root / "theme", root / "state"
            config.mkdir()
            state.mkdir()
            editorial = "# Keep this editorial comment\ncategories:\n  egg:\n    boost_keywords: [editorial-marker]\n    learned_tags: {legacy-marker: 2}\n"
            preferences = config / "preferences.yaml"
            preferences.write_text(editorial, encoding="utf-8")
            feedback, learned = state / "feedback.json", state / "learned.yaml"
            vote = {"id": "a", "at": "2026-09-01", "value": "like",
                    "keywords": ["new-marker"], "source": "Source"}
            feedback.write_text(json.dumps({"egg": [vote]}))
            with patch.dict(os.environ, {"NEWSROOM_CONFIG_DIR": str(config), "NEWSROOM_STATE_DIR": str(state)}), \
                 patch.object(update_preferences, "FEEDBACK_PATH", feedback), \
                 patch.object(update_preferences, "LEARNED_PATH", learned):
                update_preferences.main()
                first = learned.read_bytes()
                update_preferences.main()
                self.assertEqual(learned.read_bytes(), first)
                self.assertEqual(preferences.read_text(encoding="utf-8"), editorial)
                self.assertEqual(build_site.reader_vocabulary(), {"egg": ["editorial-marker", "new-marker"]})
                self.assertNotIn("learned_sources", yaml.safe_load(first)["categories"]["egg"])
                feedback.write_text(json.dumps({"egg": [{**vote, "value": "none"}]}))
                update_preferences.main()
                self.assertEqual(build_site.reader_vocabulary(), {"egg": ["editorial-marker"]})
                self.assertEqual(preferences.read_text(encoding="utf-8"), editorial)


if __name__ == "__main__":
    unittest.main()
