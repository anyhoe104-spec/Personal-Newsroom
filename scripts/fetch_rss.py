from __future__ import annotations

import hashlib
import json
import os
import re
import socket
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from collectors import COLLECTORS


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "articles.json"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
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
    impact = "自分の情報収集テーマに近い論点を深掘りする候補です。"
    egg_insight = "加工技術、商品企画、売場展開のどこに応用できるかを見る価値があります。"
    return lines, impact, egg_insight


def fallback_ai_dev_title(title: str) -> str:
    lowered = title.lower()
    keyword_titles = [
        (("voice", "audio"), "音声AIモデルとAPI活用のアップデート"),
        (("agent", "agents"), "AIエージェント活用の新しい動き"),
        (("codex",), "Codexと開発支援ワークフローのアップデート"),
        (("model", "gpt", "llm"), "AIモデルとLLM活用のアップデート"),
        (("privacy", "trusted", "cyber"), "AIの安全性・プライバシー関連アップデート"),
        (("api",), "AI API活用のアップデート"),
        (("developer", "language", "go", "python"), "開発者向けツールと実装トピック"),
    ]
    for keywords, label in keyword_titles:
        if any(keyword in lowered for keyword in keywords):
            return label
    return "AI・開発ニュースの注目アップデート"


def fallback_ai_dev_localize(title: str, description: str) -> tuple[str, list[str], str]:
    base = clean_text(description) or title
    clipped = base[:100] + ("..." if len(base) > 100 else "")
    translated_title = fallback_ai_dev_title(title)
    summary = [
        "AI・開発領域の新しい動きとして確認したい記事です。",
        f"原文タイトル: {title}",
        f"要点候補: {clipped}",
    ]
    impact = "モデル、開発ツール、API活用の判断材料として後で深掘りできます。"
    return translated_title, summary, impact


def parse_ai_json(content: str) -> dict[str, Any]:
    cleaned = content.strip().strip("`").removeprefix("json").strip()
    return json.loads(cleaned)


def ai_translate_and_summarize(
    title: str,
    description: str,
    category_key: str,
    category_label: str,
) -> tuple[str, list[str], str, str]:
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if category_key == "ai_dev" and not openai_key and not anthropic_key:
        translated_title, summary, impact = fallback_ai_dev_localize(title, description)
        return translated_title, summary, impact, ""
    if not openai_key and not anthropic_key:
        summary, impact, egg_insight = fallback_summary(title, description, category_label)
        return title, summary, impact, egg_insight

    prompt = (
        "日本語で返答してください。JSONのみを返してください。"
        "形式: {\"translated_title\":\"...\",\"summary\":[\"...\",\"...\",\"...\"],"
        "\"impact\":\"...\",\"egg_insight\":\"...\"}\n"
        f"カテゴリ: {category_label}\n原文タイトル: {title}\n本文: {description[:1500]}\n"
    )
    if category_key == "ai_dev":
        prompt += "英語タイトルの場合は自然な日本語タイトルへ翻訳してください。"
    else:
        prompt += "translated_title は原文タイトルと同じで構いません。"
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
                    "max_tokens": 700,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=25,
            )
            response.raise_for_status()
            content = response.json()["content"][0]["text"]
        parsed = parse_ai_json(content)
        translated_title = str(parsed.get("translated_title") or title)[:160]
        summary = [str(x)[:140] for x in parsed.get("summary", [])[:3]]
        while len(summary) < 3:
            summary.append("追加確認したいニュースです。")
        impact = str(parsed.get("impact", ""))[:160]
        egg_insight = str(parsed.get("egg_insight", ""))[:160]
        return translated_title, summary, impact, egg_insight
    except Exception as exc:
        print(f"[ai] summary fallback: {exc}")
        if category_key == "ai_dev":
            translated_title, summary, impact = fallback_ai_dev_localize(title, description)
            return translated_title, summary, impact, ""
        summary, impact, egg_insight = fallback_summary(title, description, category_label)
        return title, summary, impact, egg_insight


def normalize_entry(entry: dict, source: dict, category_key: str, category_label: str) -> dict | None:
    original_title = clean_text(entry.get("title", ""))
    url = entry.get("link", "")
    if not original_title or not url:
        return None
    description = clean_text(entry.get("summary", "") or entry.get("description", ""))
    translated_title, summary, impact, egg_insight = ai_translate_and_summarize(
        original_title,
        description,
        category_key,
        category_label,
    )
    source_type = source.get("source_type", "rss")
    return {
        "id": article_id(url, original_title),
        "title": translated_title,
        "original_title": original_title,
        "translated_title": translated_title,
        "url": url,
        "source": source["name"],
        "source_type": source_type,
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


def fetch_source(source: dict, category_key: str, category_label: str) -> list[dict]:
    source_type = source.get("source_type", "rss")
    collector = COLLECTORS.get(source_type)
    if collector is None:
        print(f"[source] {category_key} / {source['name']}: unsupported source_type={source_type}")
        return []
    entries = collector(source)
    articles = []
    for entry in entries:
        article = normalize_entry(entry, source, category_key, category_label)
        if article:
            articles.append(article)
    return articles


def sample_articles(category_key: str, category_label: str, count: int = 10) -> list[dict]:
    examples = {
        "business": "新規事業と市場変化を読むための経済ニュース",
        "food": "スイーツ・外食・新商品と店舗トレンド",
        "ai_dev": "AIモデル、開発ツール、API活用のアップデート",
        "egg": "卵加工品、ゆで卵、温泉卵の商品開発と技術トレンド",
    }
    now = datetime.now(timezone.utc).isoformat()
    articles = []
    for i in range(1, count + 1):
        original_title = f"{category_label} サンプル記事 {i}: {examples[category_key]}"
        url = f"https://example.com/personal-newsroom/{category_key}/{i}"
        if category_key == "ai_dev":
            translated_title, summary, impact = fallback_ai_dev_localize(original_title, examples[category_key])
            egg_insight = ""
        else:
            translated_title = original_title
            summary, impact, egg_insight = fallback_summary(original_title, examples[category_key], category_label)
        articles.append(
            {
                "id": article_id(url, original_title),
                "title": translated_title,
                "original_title": original_title,
                "translated_title": translated_title,
                "url": url,
                "source": "Fallback Sample",
                "source_type": "fallback",
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
                source_articles = fetch_source(source, category_key, category["label"])
                source_type = source.get("source_type", "rss")
                print(f"[{source_type}] {category_key} / {source['name']}: fetched {len(source_articles)} articles")
                category_articles.extend(source_articles)
            except Exception as exc:
                source_name = source.get("name", source.get("url", "unknown"))
                print(f"[source] {category_key} / {source_name}: failed: {exc}")
                continue
        if len(category_articles) < 10:
            missing = 10 - len(category_articles)
            print(f"[fallback] {category_key} / {category['label']}: adding {missing} sample articles")
            category_articles.extend(sample_articles(category_key, category["label"], missing))
        for article in category_articles:
            seen_key = f"{article['category']}:{article['id']}"
            if seen_key in seen:
                continue
            seen.add(seen_key)
            all_articles.append(article)

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(all_articles, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_articles)} articles to {DATA_PATH}")


if __name__ == "__main__":
    main()
