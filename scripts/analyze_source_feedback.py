from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_PATH = ROOT / "data" / "articles.json"
FEEDBACK_PATH = ROOT / "data" / "feedback.json"
HISTORY_PATH = ROOT / "data" / "run_history.json"
RECOMMENDATIONS_PATH = ROOT / "data" / "source_recommendations.json"
PUBLIC_HISTORY_PATH = ROOT / "public" / "run_history.json"
PUBLIC_RECOMMENDATIONS_PATH = ROOT / "public" / "source_recommendations.json"
CATEGORY_ORDER = ("business", "food", "ai_dev", "egg")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def feedback_by_source(feedback: dict[str, list[dict]]) -> dict[tuple[str, str], Counter]:
    counters: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for category, items in feedback.items():
        for item in items:
            source = str(item.get("source") or "unknown")
            value = str(item.get("value") or "")
            if value in {"like", "bad"}:
                counters[(category, source)][value] += 1
    return counters


def build_snapshot(articles: list[dict], feedback: dict[str, list[dict]]) -> dict:
    fingerprint_payload = [
        [
            article.get("category"),
            article.get("id"),
            article.get("source"),
            article.get("score"),
        ]
        for article in articles
    ]
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    generated_at = f"articles:{fingerprint}" if articles else datetime.now(timezone.utc).isoformat()
    source_feedback = feedback_by_source(feedback)
    categories: dict[str, dict] = {}
    for category in CATEGORY_ORDER:
        category_articles = [article for article in articles if article.get("category") == category]
        source_groups: dict[str, list[dict]] = defaultdict(list)
        for article in category_articles:
            source_groups[str(article.get("source") or "unknown")].append(article)
        source_metrics = {}
        for source, source_articles in sorted(source_groups.items()):
            scores = [float(article.get("score") or 0) for article in source_articles]
            feedback_counts = source_feedback.get((category, source), Counter())
            likes = int(feedback_counts.get("like", 0))
            bads = int(feedback_counts.get("bad", 0))
            source_metrics[source] = {
                "displayed": len(source_articles),
                "average_score": round(mean(scores), 1) if scores else 0.0,
                "fallback_count": sum(1 for article in source_articles if article.get("source_type") == "fallback"),
                "likes": likes,
                "bads": bads,
                "net_feedback": likes - bads,
            }
        categories[category] = {
            "displayed": len(category_articles),
            "unique_sources": len(source_groups),
            "sources": source_metrics,
        }
    return {
        "generated_at": generated_at,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "categories": categories,
    }


def merge_history(history: list[dict], snapshot: dict, limit: int = 90) -> list[dict]:
    generated_at = snapshot.get("generated_at")
    merged = [item for item in history if item.get("generated_at") != generated_at]
    merged.append(snapshot)
    return merged[-limit:]


def source_recommendation(metrics: dict) -> str:
    displayed = int(metrics.get("displayed") or 0)
    average_score = float(metrics.get("average_score") or 0)
    likes = int(metrics.get("likes") or 0)
    bads = int(metrics.get("bads") or 0)
    fallback_count = int(metrics.get("fallback_count") or 0)
    if fallback_count and fallback_count == displayed:
        return "replace_candidate"
    if bads >= likes + 2:
        return "replace_candidate"
    if displayed >= 3 and average_score < 35:
        return "watch"
    if likes >= bads + 2 or average_score >= 65:
        return "promote"
    return "keep"


def build_recommendations(history: list[dict]) -> dict:
    aggregate: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for snapshot in history:
        for category, category_metrics in snapshot.get("categories", {}).items():
            for source, metrics in category_metrics.get("sources", {}).items():
                key = (category, source)
                aggregate[key]["runs"] += 1
                aggregate[key]["displayed"] += float(metrics.get("displayed") or 0)
                aggregate[key]["score_total"] += float(metrics.get("average_score") or 0)
                aggregate[key]["likes"] += float(metrics.get("likes") or 0)
                aggregate[key]["bads"] += float(metrics.get("bads") or 0)
                aggregate[key]["fallback_count"] += float(metrics.get("fallback_count") or 0)

    categories: dict[str, dict[str, dict]] = defaultdict(dict)
    for (category, source), metrics in sorted(aggregate.items()):
        runs = max(1.0, metrics["runs"])
        summarized = {
            "runs_seen": int(metrics["runs"]),
            "average_displayed": round(metrics["displayed"] / runs, 1),
            "average_score": round(metrics["score_total"] / runs, 1),
            "likes": int(metrics["likes"]),
            "bads": int(metrics["bads"]),
            "net_feedback": int(metrics["likes"] - metrics["bads"]),
            "fallback_count": int(metrics["fallback_count"]),
        }
        summarized["recommendation"] = source_recommendation(
            {
                "displayed": summarized["average_displayed"],
                "average_score": summarized["average_score"],
                "likes": summarized["likes"],
                "bads": summarized["bads"],
                "fallback_count": summarized["fallback_count"],
            }
        )
        categories[category][source] = summarized
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "history_runs": len(history),
        "categories": categories,
    }


def main() -> None:
    articles = load_json(ARTICLES_PATH, [])
    feedback = load_json(FEEDBACK_PATH, {})
    history = load_json(HISTORY_PATH, [])
    snapshot = build_snapshot(articles, feedback)
    history = merge_history(history, snapshot)
    recommendations = build_recommendations(history)
    write_json(HISTORY_PATH, history)
    write_json(RECOMMENDATIONS_PATH, recommendations)
    write_json(PUBLIC_HISTORY_PATH, history)
    write_json(PUBLIC_RECOMMENDATIONS_PATH, recommendations)
    print(f"[source_feedback] history_runs={len(history)}")
    for category, sources in recommendations["categories"].items():
        replace_candidates = [
            source
            for source, metrics in sources.items()
            if metrics.get("recommendation") == "replace_candidate"
        ]
        print(
            f"[source_feedback] {category}: sources={len(sources)}, "
            f"replace_candidates={len(replace_candidates)}"
        )


if __name__ == "__main__":
    main()
