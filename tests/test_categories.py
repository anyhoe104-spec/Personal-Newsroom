import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import newsroom_config  # noqa: E402


class CategoryKeysTests(unittest.TestCase):
    def keys_for(self, sources_yaml: str | None):
        with tempfile.TemporaryDirectory() as directory:
            if sources_yaml is not None:
                (Path(directory) / "sources.yaml").write_text(sources_yaml, encoding="utf-8")
            with mock.patch.dict("os.environ", {"NEWSROOM_CONFIG_DIR": directory}):
                return newsroom_config.category_keys()

    def test_order_comes_from_the_theme(self):
        yaml = "categories:\n  sports: {label: S}\n  business: {label: B}\n  travel: {label: T}\n"
        self.assertEqual(self.keys_for(yaml), ("sports", "business", "travel"))

    def test_without_a_theme_the_four_legacy_keys_are_used(self):
        self.assertEqual(self.keys_for(None), newsroom_config.DEFAULT_CATEGORY_KEYS)
        self.assertEqual(self.keys_for("categories: {}\n"), newsroom_config.DEFAULT_CATEGORY_KEYS)

    def test_malformed_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            self.keys_for("categories:\n  Sports: {label: S}\n")

    def test_example_pack_keeps_the_current_four(self):
        example = Path(__file__).resolve().parents[1] / "themes" / "example"
        with mock.patch.dict("os.environ", {"NEWSROOM_CONFIG_DIR": str(example)}):
            self.assertEqual(newsroom_config.category_keys(), ("business", "food", "ai_dev", "egg"))


if __name__ == "__main__":
    unittest.main()


class CategorySettingsTests(unittest.TestCase):
    def settings_for(self, sources_yaml, key):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "sources.yaml").write_text(sources_yaml, encoding="utf-8")
            with mock.patch.dict("os.environ", {"NEWSROOM_CONFIG_DIR": directory}):
                return newsroom_config.category_settings(key), newsroom_config.translation_categories()

    def test_legacy_keys_keep_their_behaviour_without_settings(self):
        yaml = "categories:\n  business: {}\n  food: {}\n  ai_dev: {}\n  egg: {}\n"
        settings, translate = self.settings_for(yaml, "ai_dev")
        self.assertEqual(settings, {"profile": "ai_dev", "translate": True, "preserve_subject": True, "source_limit": 4})
        self.assertEqual(translate, ("ai_dev", "egg"))
        self.assertEqual(self.settings_for(yaml, "egg")[0]["profile"], "egg")
        self.assertEqual(self.settings_for(yaml, "business")[0], {"profile": None, "translate": False, "preserve_subject": False, "source_limit": 6})

    def test_a_new_category_starts_plain_and_can_opt_in(self):
        yaml = (
            "categories:\n"
            "  sports: {}\n"
            "  tech: {translate: true, profile: ai_dev, source_limit: 3}\n"
            "  egg: {profile: null, translate: false}\n"
        )
        self.assertEqual(self.settings_for(yaml, "sports")[0], {"profile": None, "translate": False, "preserve_subject": False, "source_limit": None})
        tech, translate = self.settings_for(yaml, "tech")
        self.assertEqual((tech["profile"], tech["translate"], tech["source_limit"]), ("ai_dev", True, 3))
        self.assertEqual(translate, ("tech",))
        # A theme can switch a legacy key's special handling off.
        self.assertIsNone(self.settings_for(yaml, "egg")[0]["profile"])

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            self.settings_for("categories:\n  sports: {profile: football}\n", "sports")
