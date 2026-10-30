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
