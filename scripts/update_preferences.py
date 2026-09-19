from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml
from newsroom_config import state_path
from newsroom_logging import get_logger

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = state_path("feedback.json")
LEARNED_PATH = state_path("learned.yaml")
LOG = get_logger()
CATEGORIES = ("business", "food", "ai_dev", "egg")


def learned_preferences(prefs: dict, feedback: dict) -> dict:
    """Recompute derived tags. Never append learned words into editorial keywords.

    Re-running is idempotent; retracting or reversing a vote removes its influence.
    Browser-local learning works without uploading this optional feedback export.
    """
    for category in CATEGORIES:
        tags = Counter()
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
        category_prefs = prefs.setdefault("categories", {}).setdefault(category, {})
        category_prefs["learned_tags"] = dict(sorted((k, max(-3, min(3, v))) for k, v in tags.items() if v))
        # Source feedback is already consumed by score_articles.feedback_score.
        # Do not persist a second, unused copy of the same signal.
        category_prefs.pop("learned_sources", None)
    return prefs


def main() -> None:
    if not FEEDBACK_PATH.exists():
        LOG.warning("No feedback.json found")
        return
    feedback = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
    learned = learned_preferences({}, feedback)
    LEARNED_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = LEARNED_PATH.with_suffix(".yaml.tmp")
    temporary.write_text(yaml.safe_dump(learned, allow_unicode=True, sort_keys=False), encoding="utf-8")
    temporary.replace(LEARNED_PATH)
    LOG.info("Updated derived RSS tags in state; editorial preferences unchanged")


if __name__ == "__main__":
    main()
