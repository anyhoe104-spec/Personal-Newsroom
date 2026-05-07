from __future__ import annotations

import hashlib
import json
import os
import re
import socket
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests
import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "articles.json"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
PROMPTS_PATH = ROOT / "config" / "prompts.yaml"
socket.setdefaulttimeout(20)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def article_id(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode("utf-8")).hexdigest()[:16]


def parse_date(entry: dict) -> str:
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            continue
    return datetime.now(timezone.utc).isoformat()


def fallback_summary(title: str, description: str, category_label: str) -> tuple[list[str], str, str]:
    base = clean_text(description) or title
    clipped = base[:90] + ("..." if len(base) > 90 else "")
    lines = [
        f"{category_label}で注目したい動きです。",
        clipped,
        "今後の事業・開発・購買判断のヒントとして確認します。",
    ]
    impact = "自分の情報収集テーマに近い論点なら深掘り候補です。"
    egg_insight = "加工技術・商品企画・売場展開のどこに応用できるかを見る価値があります。"
    return lines, impact, egg_insight


def summarize_with_ai(title: str, description: str, category_key: str, category_label: str) -> tuple[list[str], str, str]:
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not openai_key and not anthropic_key:
        return fallback_summary(title, description, category_label)

    prompt = (
        "日本語で返答してください。JSONのみを返してください。"
        "形式: {\"summary\":[\"...\",\"...\",\"...\"],\"impact\":\"...\",\"egg_insight\":\"...\"}\n"
        f"カテゴリ: {category_label}\nタイトル: {title}\n本文: {description[:1500]}\n"
    )
    if category_key != "egg":
        prompt += "egg_insight は空文字にしてください。"

    try:
        if openai_key:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
                timeout=25,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        else:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=25,
            )
            response.raise_for_status()
            content = response.json()["content"][0]["text"]
        parsed = json.loads(content.strip().strip("`").removeprefix("json").strip())
        summary = [str(x)[:120] for x in parsed.get("summary", [])[:3]]
        while len(summary) < 3:
            summary.append("追加確認したいニュースです。")
        return summary, str(parsed.get("impact", ""))[:140], str(parsed.get("egg_insight", ""))[:140]
    except Exception:
        return fallback_summary(title, description, category_label)


def fetch_feed(source: dict, category_key: str, category_label: str) -> list[dict]:
    feed = feedparser.parse(source["url"])
    articles = []
    for entry in feed.entries[:30]:
        title = clean_text(entry.get("title", ""))
        url = entry.get("link", "")
        if not title or not url:
            continue
        description = clean_text(entry.get("summary", "") or entry.get("description", ""))
        summary, impact, egg_insight = summarize_with_ai(title, description, category_key, category_label)
        articles.append(
            {
                "id": article_id(url, title),
                "title": title,
                "url": url,
                "source": source["name"],
                "source_region": source.get("region", "jp"),
                "category": category_key,
                "category_label": category_label,
                "published_at": parse_date(entry),
                "raw_summary": description,
                "summary": summary,
                "impact": impact,
                "egg_insight": egg_insight if category_key == "egg" else "",
                "score": 0,
            }
        )
    return articles


def sample_articles(category_key: str, category_label: str, count: int = 10) -> list[dict]:
    examples = {
        "business": "新規事業と市場変化を読むための経営ニュース",
        "food": "スイーツ・外食の商品開発と店舗トレンド",
        "ai_dev": "AIモデル、開発ツール、API活用のアップデート",
        "egg": "卵加工品・ゆで卵・温泉卵の商品開発と技術トレンド",
    }
    now = datetime.now(timezone.utc).isoformat()
    articles = []
    for i in range(1, count + 1):
        title = f"{category_label} サンプル記事 {i}: {examples[category_key]}"
        url = f"https://example.com/personal-newsroom/{category_key}/{i}"
        summary, impact, egg_insight = fallback_summary(title, examples[category_key], category_label)
        articles.append(
            {
                "id": article_id(url, title),
                "title": title,
                "url": url,
                "source": "Fallback Sample",
                "source_region": "jp",
                "category": category_key,
                "category_label": category_label,
                "published_at": now,
                "raw_summary": examples[category_key],
                "summary": summary,
                "impact": impact,
                "egg_insight": egg_insight if category_key == "egg" else "",
                "score": 0,
            }
        )
    return articles


def main() -> None:
    sources = load_yaml(SOURCES_PATH)["categories"]
    all_articles: list[dict] = []
    seen: set[str] = set()
    for category_key, category in sources.items():
        category_articles: list[dict] = []
        for source in category.get("sources", []):
            try:
                category_articles.extend(fetch_feed(source, category_key, category["label"]))
            except Exception:
                continue
        if len(category_articles) < 10:
            category_articles.extend(sample_articles(category_key, category["label"], 10 - len(category_articles)))
        for article in category_articles:
            if article["id"] in seen:
                continue
            seen.add(article["id"])
            all_articles.append(article)

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(all_articles, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_articles)} articles to {DATA_PATH}")


if __name__ == "__main__":
    main()
