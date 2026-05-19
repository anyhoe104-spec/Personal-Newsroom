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
ANTHROPIC_TRANSLATION_LIMIT = 10
ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
socket.setdefaulttimeout(20)
anthropic_translation_count = 0


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


existing_articles_by_id: dict[str, dict] = {
    article.get("id"): article
    for article in load_json(DATA_PATH, [])
    if isinstance(article, dict) and article.get("id")
}


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
            model = os.getenv("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
            headers = {
                "x-api-key": anthropic_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            }
            response = requests.post(
                ANTHROPIC_MESSAGES_ENDPOINT,
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": 700,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=25,
            )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                log_anthropic_http_error(exc, model, headers)
                raise
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
                "translated_summary": summary if category_key == "ai_dev" else [],
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


def has_japanese_text(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text or ""))


def is_english_article(title: str, description: str) -> bool:
    text = f"{title} {description}"
    if has_japanese_text(text):
        return False
    return len(re.findall(r"[A-Za-z]{3,}", text)) >= 3


def call_anthropic_haiku(title: str, description: str) -> tuple[str, list[str], str]:
    model = os.getenv("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    prompt = (
        "Translate, summarize, and explain the impact of this English AI/developer news article "
        "for a Japanese reader building personal news and AI workflow tools. "
        "Return only JSON with this shape: "
        '{"translated_title":"...","translated_summary":["...","...","..."],"impact":"..."}. '
        "All values must be natural Japanese. Do not output English boilerplate. "
        "translated_summary must contain three concise Japanese bullet-style points. "
        "impact must be a practical Japanese comment about how this can inform AI workflow design, "
        "developer operations, product planning, or newsroom automation.\n"
        f"Title: {title}\n"
        f"Article text: {description[:1500]}\n"
    )
    response = requests.post(
        ANTHROPIC_MESSAGES_ENDPOINT,
        headers=headers,
        json={
            "model": model,
            "max_tokens": 700,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=25,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        log_anthropic_http_error(exc, model, headers)
        raise
    content = response.json()["content"][0]["text"]
    parsed = parse_ai_json(content)
    translated_title = str(parsed.get("translated_title") or title)[:160]
    translated_summary = [str(x)[:140] for x in parsed.get("translated_summary", [])[:3] if str(x).strip()]
    impact = str(parsed.get("impact") or "")[:180]
    return translated_title, translated_summary, impact


def log_anthropic_http_error(exc: requests.HTTPError, model: str, headers: dict[str, str]) -> None:
    response = exc.response
    status_code = response.status_code if response is not None else "unknown"
    response_url = response.url if response is not None else ANTHROPIC_MESSAGES_ENDPOINT
    header_names = ", ".join(sorted(headers.keys()))
    print(
        "[anthropic] api error: "
        f"status={status_code}, endpoint={response_url}, model={model}, "
        f"headers=[{header_names}], api_key_present={bool(os.getenv('ANTHROPIC_API_KEY'))}"
    )
    if status_code == 404:
        print(
            "[anthropic] 404 diagnostic: endpoint should be "
            f"{ANTHROPIC_MESSAGES_ENDPOINT}; check model availability/access for "
            f"{model} and required headers x-api-key, anthropic-version, content-type. "
            "API key value was not logged."
        )


def existing_translated_article(article_id_value: str) -> dict | None:
    article = existing_articles_by_id.get(article_id_value)
    if article and article.get("translated_title"):
        return article
    return None


def maybe_translate_ai_dev_with_haiku(
    article_id_value: str,
    title: str,
    description: str,
    category_key: str,
) -> tuple[str, list[str], str] | None:
    global anthropic_translation_count

    existing_article = existing_translated_article(article_id_value)
    if category_key == "ai_dev" and existing_article:
        translated_summary = existing_article.get("translated_summary") or existing_article.get("summary") or []
        impact = str(existing_article.get("impact") or "")
        return str(existing_article["translated_title"]), [str(x) for x in translated_summary[:3]], impact
    if category_key != "ai_dev":
        return None
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    if anthropic_translation_count >= ANTHROPIC_TRANSLATION_LIMIT:
        return None
    if not is_english_article(title, description):
        return None

    try:
        translated_title, translated_summary, impact = call_anthropic_haiku(title, description)
        anthropic_translation_count += 1
        print(f"[anthropic] ai_dev translated {anthropic_translation_count}/{ANTHROPIC_TRANSLATION_LIMIT}: {title[:80]}")
        return translated_title, translated_summary, impact
    except Exception as exc:
        print(f"[anthropic] ai_dev translation fallback: {exc}")
        return None


def ai_translate_and_summarize(
    title: str,
    description: str,
    category_key: str,
    category_label: str,
    article_id_value: str,
) -> tuple[str, list[str], list[str], str, str]:
    haiku_translation = maybe_translate_ai_dev_with_haiku(
        article_id_value,
        title,
        description,
        category_key,
    )
    if haiku_translation:
        translated_title, translated_summary, impact = haiku_translation
        summary = translated_summary if translated_summary else [description or title]
        while len(summary) < 3:
            summary.append("")
        if not impact:
            impact = "自社向けAIワークフロー設計やニュースアプリの自動化改善に応用余地があります。"
        return translated_title, summary[:3], translated_summary[:3], impact, ""

    if category_key == "ai_dev":
        translated_title, summary, impact = fallback_ai_dev_localize(title, description)
        return translated_title, summary, summary, impact, ""

    summary, impact, egg_insight = fallback_summary(title, description, category_label)
    return title, summary, [], impact, egg_insight


def normalize_entry(entry: dict, source: dict, category_key: str, category_label: str) -> dict | None:
    original_title = clean_text(entry.get("title", ""))
    url = entry.get("link", "")
    if not original_title or not url:
        return None
    description = clean_text(entry.get("summary", "") or entry.get("description", ""))
    article_id_value = article_id(url, original_title)
    translated_title, summary, translated_summary, impact, egg_insight = ai_translate_and_summarize(
        original_title,
        description,
        category_key,
        category_label,
        article_id_value,
    )
    source_type = source.get("source_type", "rss")
    return {
        "id": article_id_value,
        "title": translated_title,
        "original_title": original_title,
        "translated_title": translated_title,
        "translated_summary": translated_summary,
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
