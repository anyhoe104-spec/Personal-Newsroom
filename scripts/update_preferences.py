from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml
from newsroom_logging import get_logger

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = ROOT / "data" / "feedback.json"
PREFERENCES_PATH = ROOT / "config" / "preferences.yaml"
LOG = get_logger()
CATEGORIES = ("business", "food", "ai_dev", "egg")


def learned_preferences(prefs: dict, feedback: dict) -> dict:
    """Recompute derived tags. Never append learned words into editorial keywords.

    Re-running is idempotent; retracting or reversing a vote removes its influence.
    Browser-local learning works without uploading this optional feedback export.
    """
    for category in CATEGORIES:
        tags, sources = Counter(), Counter()
        rows = feedback.get(category, [])
        latest = {}
        for row in rows:
            key = row.get("id")
            if key and (key not in latest or row.get("at", "") >= latest[key].get("at", "")):
                latest[key] = row
        for row in latest.values():
            if row.get("value") not in {"like", "bad"} or row.get("source_type") == "fallback":
                continue
            direction = 1 if row["value"] == "like" else -1
            for word in set(row.get("keywords", [])):
                if isinstance(word, str) and 2 <= len(word) <= 50:
                    tags[word] += direction
            if row.get("source"):
                sources[row["source"]] += direction
        category_prefs = prefs.setdefault("categories", {}).setdefault(category, {})
        category_prefs["learned_tags"] = dict(sorted((k, max(-3, min(3, v))) for k, v in tags.items() if v))
        category_prefs["learned_sources"] = dict(sorted((k, max(-3, min(3, v))) for k, v in sources.items() if v))
    return prefs


def main() -> None:
    if not FEEDBACK_PATH.exists():
        LOG.warning("No feedback.json found")
        return
    feedback = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
    prefs = yaml.safe_load(PREFERENCES_PATH.read_text(encoding="utf-8")) or {}
    prefs = learned_preferences(prefs, feedback)
    PREFERENCES_PATH.write_text(yaml.safe_dump(prefs, allow_unicode=True, sort_keys=False), encoding="utf-8")
    LOG.info("Updated derived RSS tags and source preferences")


if __name__ == "__main__":
    main()
