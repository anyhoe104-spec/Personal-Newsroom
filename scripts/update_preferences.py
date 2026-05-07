from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = ROOT / "data" / "feedback.json"
PREFERENCES_PATH = ROOT / "config" / "preferences.yaml"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_+#.-]+|[\u3040-\u30ff\u3400-\u9fff]+", text.lower())


def main() -> None:
    if not FEEDBACK_PATH.exists():
        print("No feedback.json found")
        return
    feedback = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
    prefs = yaml.safe_load(PREFERENCES_PATH.read_text(encoding="utf-8")) or {}

    for category, items in feedback.items():
        likes = [item for item in items if item.get("value") == "like"]
        bads = [item for item in items if item.get("value") == "bad"]
        like_words = Counter(word for item in likes for word in item.get("keywords", tokenize(item.get("title", ""))))
        bad_words = Counter(word for item in bads for word in item.get("keywords", tokenize(item.get("title", ""))))
        category_prefs = prefs.setdefault("categories", {}).setdefault(category, {})
        boosts = list(dict.fromkeys(category_prefs.get("boost_keywords", []) + [w for w, _ in like_words.most_common(8)]))
        downs = list(dict.fromkeys(category_prefs.get("downrank_keywords", []) + [w for w, _ in bad_words.most_common(8)]))
        category_prefs["boost_keywords"] = boosts[:40]
        category_prefs["downrank_keywords"] = downs[:30]

    PREFERENCES_PATH.write_text(yaml.safe_dump(prefs, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Updated {PREFERENCES_PATH}")


if __name__ == "__main__":
    main()
