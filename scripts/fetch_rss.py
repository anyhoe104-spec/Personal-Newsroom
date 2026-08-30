from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from collectors import COLLECTORS
from newsroom_logging import (
    get_logger,
    log_capped,
    log_suppression_summary,
)
from score_articles import egg_article_is_relevant, enforce_category_limits, score_article


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "articles.json"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
PREFERENCES_PATH = ROOT / "config" / "preferences.yaml"
FEEDBACK_PATH = ROOT / "data" / "feedback.json"
LOG = get_logger()
ANTHROPIC_TRANSLATION_LIMIT = 10
AI_TRANSLATION_SUMMARY_KEYS = (
    "api_key_present",
    "model",
    "request_count",
    "api_success",
    "source_japanese_count",
    "source_english_count",
    "japanese_passthrough_count",
    "response_count",
    "matched_count",
    "meaningful_translation_count",
    "generic_translation_count",
    "fallback_count",
    "request_display_match_count",
    "final_display_translated_count",
    "final_display_untranslated_count",
)
ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_ANTHROPIC_MAX_TOKENS = 6000
socket.setdefaulttimeout(20)
anthropic_translation_count = 0
anthropic_batch_requested = False
anthropic_last_response_count = 0
anthropic_last_matched_count = 0
anthropic_last_generic_translation_count = 0
RUN_STATS: dict[str, Any] = {
    "rss_sources": [],
    "fallback_by_category": {},
    "ai_translation": {
        "api_key_present": False,
        "model": DEFAULT_ANTHROPIC_MODEL,
        "request_count": 0,
        "response_count": 0,
        "matched_count": 0,
        "meaningful_translation_count": 0,
        "generic_translation_count": 0,
        "fallback_count": 0,
        "api_success": 0,
        "source_japanese_count": 0,
        "source_english_count": 0,
        "japanese_passthrough_count": 0,
        "final_display_translated_count": 0,
        "final_display_untranslated_count": 0,
        "request_display_match_count": 0,
    },
}


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


def console_safe(value: str) -> str:
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    if encoding.replace("-", "_") not in ("cp932", "shift_jis", "ms_kanji"):
        return value
    return value.encode("cp932", errors="backslashreplace").decode("cp932")


def log_safe(value: str, level: int = logging.INFO) -> None:
    LOG.log(level, console_safe(value))


def summarize_exception(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None):
        status_code = response.status_code
        reason = getattr(response, "reason", "") or ""
        return f"{status_code} {reason}".strip()
    message = str(exc).strip()
    return message[:160] if message else exc.__class__.__name__


def record_source_result(category: str, source: dict, fetched_count: int, failed_reason: str = "") -> None:
    source_name = source.get("name", source.get("url", "unknown"))
    source_type = source.get("source_type", source.get("type", "rss"))
    result = {
        "category": category,
        "source": source_name,
        "source_type": source_type,
        "fetched_count": fetched_count,
        "failed_reason": failed_reason,
    }
    RUN_STATS["rss_sources"].append(result)
    if failed_reason:
        log_safe(f"[rss_failure] {category} / {source_name} / {source_type}: {failed_reason}", logging.WARNING)
    elif fetched_count == 0:
        log_safe(f"[rss_zero] {category} / {source_name} / {source_type}: 0 articles", logging.WARNING)
    else:
        log_safe(f"[rss_summary] {category} / {source_name} / {source_type}: fetched={fetched_count}")


def count_by_category(articles: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for article in articles:
        category = str(article.get("category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def normalize_source(source: dict) -> dict:
    normalized = dict(source)
    normalized["source_type"] = normalized.get("source_type") or normalized.pop("type", "rss")
    return normalized


def normalized_categories(config: dict) -> dict[str, dict]:
    categories = config.get("categories", {}) or {}
    normalized = {
        category_key: {**category, "sources": [normalize_source(source) for source in category.get("sources", [])]}
        for category_key, category in categories.items()
    }
    for source in config.get("sources", []) or []:
        category_key = source.get("category")
        if category_key not in normalized:
            LOG.warning(f"[source_config] ignored uncategorized source: {source.get('name', source.get('url', 'unknown'))}")
            continue
        normalized_source = normalize_source({k: v for k, v in source.items() if k != "category"})
        normalized[category_key].setdefault("sources", []).append(normalized_source)
        LOG.info(f"[source_config] migrated top-level source into {category_key}: {normalized_source.get('name')}")
    return normalized


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
    return f"翻訳未取得: {title[:120]}"


def fallback_ai_dev_localize(title: str, description: str) -> tuple[str, list[str], str]:
    translated_title = fallback_ai_dev_title(title)
    summary = [
        "翻訳未取得のため、原文情報をもとに仮表示しています。",
        "Claude翻訳に成功すると、ここに日本語の要約3点が表示されます。",
        "詳細は記事リンク先の原文を確認してください。",
    ]
    impact = "翻訳未取得です。APIキー、モデル名、Anthropic APIの応答状況を確認してください。"
    return translated_title, summary, impact


def article_level_ai_dev_fallback(title: str, description: str) -> tuple[str, list[str], str]:
    base = clean_text(description) or title
    title_hint = clean_text(title)[:90]
    body_hint = base[:90] + ("..." if len(base) > 90 else "")
    translated_title = f"要確認: {title_hint}"[:160]
    summary = [
        f"原題は「{title_hint}」。Claude翻訳結果が不十分だったため個別確認対象です。",
        f"本文の手がかり: {body_hint}",
        "正式な日本語要約は記事本文を確認して差し替える必要があります。",
    ]
    impact = f"「{title_hint[:38]}」はAI開発ワークフローや製品判断への影響確認が必要です。"
    return translated_title, summary, impact


def ai_dev_fallback_title(title: str) -> str:
    return f"要確認: {clean_text(title)[:90]}"[:160]


def strip_code_fences(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def remove_control_chars(content: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", content)


def extract_json_array(content: str) -> str:
    start = content.find("[")
    end = content.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in Anthropic response")
    return content[start : end + 1]


def response_preview_from_payload(payload: dict) -> str:
    preview_source = json.dumps(payload, ensure_ascii=False)
    return remove_control_chars(preview_source).replace("\n", " ")[:300]


def response_content_types(payload: dict) -> list[str]:
    return [str(block.get("type", "unknown")) for block in payload.get("content", []) if isinstance(block, dict)]


def anthropic_max_tokens() -> int:
    raw_value = os.getenv("ANTHROPIC_MAX_TOKENS")
    if not raw_value:
        return DEFAULT_ANTHROPIC_MAX_TOKENS
    try:
        return max(2400, int(raw_value))
    except ValueError:
        return DEFAULT_ANTHROPIC_MAX_TOKENS


def log_json_parse_failure(content: str, exc: Exception, payload: dict | None = None) -> None:
    preview = remove_control_chars(strip_code_fences(content)).replace("\n", " ")[:300]
    if not preview and payload is not None:
        preview = response_preview_from_payload(payload)
    LOG.warning(f"[anthropic] json parse failed: {exc}; response_preview={preview!r}")


def count_articles_in_messages_payload(request_body: dict) -> int:
    messages = request_body.get("messages") or []
    if not messages or not isinstance(messages[0], dict):
        return 0
    content = str(messages[0].get("content") or "")
    match = re.search(r"Articles JSON:\s*(\[.*?\])\s*(?:\n|$)", content, flags=re.DOTALL)
    if not match:
        return 0
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return 0
    return len(parsed) if isinstance(parsed, list) else 0


def parse_ai_json(content: str) -> Any:
    cleaned = remove_control_chars(strip_code_fences(content))
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            return json.loads(extract_json_array(cleaned))
        except Exception as exc:
            log_json_parse_failure(content, exc)
            raise


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
        log_capped(logging.WARNING, "ai_summary_fallback", f"[ai] summary fallback: {exc}", limit=5)
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
        LOG.warning(f"[source] {category_key} / {source['name']}: unsupported source_type={source_type}")
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
            _, summary, impact = fallback_ai_dev_localize(original_title, examples[category_key])
            translated_title = original_title
            translated_summary = []
            fallback_title = ai_dev_fallback_title(original_title)
            egg_insight = ""
        else:
            translated_title = original_title
            summary, impact, egg_insight = fallback_summary(original_title, examples[category_key], category_label)
            translated_summary = []
            fallback_title = ""
        articles.append(
            {
                "id": article_id(url, original_title),
                "title": translated_title,
                "original_title": original_title,
                "display_title": translated_title,
                "translated_title": translated_title,
                "translated_summary": translated_summary,
                "fallback_title": fallback_title,
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


def is_japanese_article(title: str, description: str) -> bool:
    return has_japanese_text(f"{title} {description}")


def starts_with_ascii_word(text: str) -> bool:
    return bool(re.match(r"^\s*[A-Za-z][A-Za-z0-9'’:-]*\b", text or ""))


def looks_like_english_text(text: str) -> bool:
    if not text.strip():
        return True
    ascii_words = re.findall(r"[A-Za-z]{3,}", text)
    japanese_chars = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", text)
    if not japanese_chars:
        return len(ascii_words) >= 3
    return starts_with_ascii_word(text) and len(ascii_words) >= max(4, len(japanese_chars))


def is_generic_ai_dev_title(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title or "")
    generic_markers = (
        "AI・開発ニュースの注目アップデート",
        "AI開発ニュースの注目アップデート",
        "AIと開発ニュースの注目アップデート",
        "AIモデルとLLM活用のアップデート",
        "AIエージェント活用の新しい動き",
        "Codexと開発支援ワークフローのアップデート",
        "AIAPI活用のアップデート",
        "翻訳未取得:",
        "翻訳未取得：",
        "要確認:",
        "要確認：",
        "Claude翻訳",
    )
    if any(marker.replace(" ", "") in normalized for marker in generic_markers):
        return True
    if looks_like_english_text(title):
        return True
    generic_titles = (
        "音声AIモデルとAPI活用のアップデート",
        "AIエージェント活用の新しい動き",
        "Codexと開発支援ワークフローのアップデート",
        "AIモデルとLLM活用のアップデート",
        "AIの安全性・プライバシー関連アップデート",
        "AI API活用のアップデート",
        "開発者向けツールと実装トピック",
        "AI・開発ニュースの注目アップデート",
    )
    return title in generic_titles or title.startswith("翻訳未取得:")


def significant_ascii_tokens(text: str) -> set[str]:
    stop_words = {
        "about",
        "after",
        "ahead",
        "article",
        "builds",
        "class",
        "come",
        "comes",
        "frontier",
        "future",
        "futures",
        "learns",
        "models",
        "new",
        "news",
        "pulling",
        "running",
        "safely",
        "service",
        "smarter",
        "trusted",
        "want",
        "while",
        "with",
        "world",
    }
    tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{2,}", text or "")
        if token.lower() not in stop_words
    }
    return tokens


def title_preserves_original_subject(translated_title: str, original_title: str) -> bool:
    original_tokens = significant_ascii_tokens(original_title)
    if not original_tokens:
        return True
    translated_lower = translated_title.lower()
    return any(token in translated_lower for token in original_tokens)


def is_generic_ai_dev_impact(impact: str) -> bool:
    normalized = re.sub(r"\s+", "", impact or "")
    generic_markers = (
        "翻訳未取得です。",
        "APIキー、モデル名、AnthropicAPIの応答状況を確認してください",
        "自社向けAIワークフロー設計やニュースアプリの自動化改善に応用余地があります",
        "自分の情報収集テーマに近い論点を深掘りする候補です",
        "今後の事業・開発・購買判断のヒントとして確認します",
        "AIanddevelopertopictranslated",
    )
    if any(marker.replace(" ", "") in normalized for marker in generic_markers):
        return True
    return looks_like_english_text(impact)


def looks_like_untranslated_summary(lines: list) -> bool:
    joined = " ".join(str(line) for line in lines)
    extra_blocked_markers = (
        "Claude翻訳に成功すると",
        "翻訳未取得",
        "原文タイトル",
        "AI and developer topic translated",
    )
    if len([line for line in lines if str(line).strip()]) != 3:
        return True
    if any(marker in joined for marker in extra_blocked_markers):
        return True
    if looks_like_english_text(joined):
        return True
    blocked_markers = ("原文タイトル:", "要点候補:", "Article URL", "http://", "https://")
    if any(marker in joined for marker in blocked_markers):
        return True
    if not joined.strip():
        return True
    return not has_japanese_text(joined)


def usable_ai_dev_translation(article: dict) -> bool:
    translated_title = str(article.get("translated_title") or "")
    translated_summary = article.get("translated_summary") or article.get("summary") or []
    impact = str(article.get("impact") or "")
    original_title = str(article.get("original_title") or "")
    return (
        bool(translated_title)
        and has_japanese_text(translated_title)
        and not is_generic_ai_dev_title(translated_title)
        and title_preserves_original_subject(translated_title, original_title)
        and not looks_like_untranslated_summary(translated_summary)
        and has_japanese_text(impact)
        and not is_generic_ai_dev_impact(impact)
    )


def call_anthropic_haiku_batch(items: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    global anthropic_last_generic_translation_count
    global anthropic_last_matched_count
    global anthropic_last_response_count

    model = os.getenv("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    article_payload = [
        {
            "stable_id": item["stable_id"],
            "title": item["title"],
            "text": item["description"][:700],
        }
        for item in items
    ]
    first_article = article_payload[0] if article_payload else {}
    LOG.debug(
        "[anthropic] request articles before prompt: "
        f"request_article_count={len(article_payload)}, "
        f"first_article_stable_id={first_article.get('stable_id', '')!r}, "
        f"first_article_title={console_safe(str(first_article.get('title', ''))[:160])!r}"
    )
    prompt = (
        "Translate, summarize, and explain the impact of these English AI/developer news articles "
        "for a Japanese reader building personal news and AI workflow tools. "
        "Use the save_ai_dev_translations tool. If tool use is unavailable, return only a JSON array "
        "with no markdown, comments, or surrounding text. Each array item must have this shape: "
        '{"stable_id":"ai_dev_0","translated_title":"...","translated_summary":["...","...","..."],"impact":"..."}. '
        "Return one item for every input stable_id and preserve each stable_id exactly. "
        "All values must be natural Japanese. Do not output English boilerplate. "
        "translated_title must reflect the specific meaning of the original title; do not use generic titles "
        "such as AIモデルとLLM活用のアップデート or AIエージェント活用の新しい動き. "
        "If the article text is only a URL or thin metadata, infer the Japanese title and summary from the title. "
        "translated_title must be 80 Japanese characters or fewer. "
        "translated_summary must contain exactly three concise Japanese bullet-style points, each 70 Japanese characters or fewer, and must not include "
        "原文タイトル, 要点候補, Article URL, or raw English summary text. "
        "impact must be 90 Japanese characters or fewer and must be a practical Japanese comment about how this can inform AI workflow design, "
        "developer operations, product planning, or newsroom automation.\n"
        f"Articles JSON: {json.dumps(article_payload, ensure_ascii=False)}\n"
    )
    prompt += (
        "\nStrict Japanese quality rules:\n"
        "- translated_title must be a concrete Japanese localization of the original title, preserving the subject, company/product name, event, and claim.\n"
        "- Never use generic titles such as AI・開発ニュースの注目アップデート, AIモデルとLLM活用のアップデート, "
        "AIエージェント活用の新しい動き, or Codexと開発支援ワークフローのアップデート.\n"
        "- Do not output fallback phrases such as 翻訳未取得 or Claude翻訳に成功すると.\n"
        "- translated_summary must contain exactly three concise Japanese points based on the original content.\n"
        "- Do not include labels like 原文タイトル, 要約, Article URL, URLs, or raw English summary text.\n"
        "- impact must state an article-specific implication; avoid fixed generic comments.\n"
        "- Every returned field must be Japanese. Product names such as OpenAI, Codex, Gemini, and GPT may remain as names.\n"
    )
    prompt = (
        "Use the save_ai_dev_translations tool to return Japanese translations for every article in Articles JSON. "
        "Preserve each stable_id exactly and return exactly one tool article per input article. "
        "translated_title: concrete Japanese localization of the original title, 80 Japanese characters or fewer. "
        "Do not use generic or fallback titles such as AI・開発ニュースの注目アップデート, 翻訳未取得, or 要確認. "
        "translated_summary: exactly three concise Japanese points based on the article, 70 Japanese characters or fewer each. "
        "impact: article-specific Japanese implication for AI workflow, developer operations, product planning, or newsroom automation, 90 Japanese characters or fewer. "
        "All fields must be Japanese except product/company names such as OpenAI, Codex, Gemini, GPT, Warp, and CUDA.\n"
        f"Articles JSON: {json.dumps(article_payload, ensure_ascii=False)}\n"
    )
    tool_schema = anthropic_translation_tool_schema()
    request_body = {
        "model": model,
        "max_tokens": anthropic_max_tokens(),
        "messages": [{"role": "user", "content": prompt}],
        "tools": [tool_schema],
        "tool_choice": {"type": "tool", "name": "save_ai_dev_translations"},
    }
    summary_schema = tool_schema["input_schema"]["properties"]["articles"]["items"]["properties"]["translated_summary"]
    LOG.debug(
        "[anthropic] request messages payload: "
        f"articles_count={count_articles_in_messages_payload(request_body)}, "
        f"max_tokens={request_body['max_tokens']}, "
        f"tool_articles_required={'articles' in tool_schema['input_schema'].get('required', [])}, "
        f"translated_summary_min_items={summary_schema.get('minItems')}, "
        f"translated_summary_max_items={summary_schema.get('maxItems')}"
    )
    response = post_anthropic_with_backoff(headers, request_body, model)
    parsed = extract_batch_items_from_anthropic_response(response)

    translations: dict[str, dict[str, Any]] = {}
    parse_failures = 0
    matched_count = 0
    requested_stable_ids = {item["stable_id"] for item in items}
    original_title_by_stable_id = {item["stable_id"]: item.get("title", "") for item in items}
    for item in parsed:
        if not isinstance(item, dict) or not item.get("stable_id"):
            parse_failures += 1
            continue
        stable_id = str(item["stable_id"])
        if stable_id not in requested_stable_ids:
            parse_failures += 1
            log_capped(
                logging.WARNING,
                "anthropic_unknown_stable_id",
                f"[anthropic] discarded unknown stable_id={stable_id}",
            )
            continue
        matched_count += 1
        translated_summary = [
            str(x)[:140]
            for x in item.get("translated_summary", [])[:3]
            if str(x).strip()
        ]
        article_translation = {
            "translated_title": str(item.get("translated_title") or "")[:160],
            "translated_summary": translated_summary,
            "impact": str(item.get("impact") or "")[:180],
            "original_title": original_title_by_stable_id.get(stable_id, ""),
        }
        if usable_ai_dev_translation(article_translation):
            translations[stable_id] = article_translation
        else:
            parse_failures += 1
            log_capped(
                logging.WARNING,
                "anthropic_weak_translation",
                f"[anthropic] discarded weak ai_dev translation for stable_id={stable_id}",
            )
    anthropic_last_response_count = len(parsed)
    anthropic_last_matched_count = matched_count
    anthropic_last_generic_translation_count = matched_count - len(translations)
    LOG.info(
        "[anthropic] ai_dev parse results: "
        f"matched_count={matched_count}, meaningful_translation_count={len(translations)}, "
        f"generic_translation_count={anthropic_last_generic_translation_count}, "
        f"parse_failed={parse_failures}, fallback_count={len(items) - len(translations)}"
    )
    return translations


def anthropic_translation_tool_schema() -> dict:
    return {
        "name": "save_ai_dev_translations",
        "description": "Save Japanese translations for AI/developer news articles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "articles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "stable_id": {"type": "string"},
                            "translated_title": {"type": "string", "maxLength": 80},
                            "translated_summary": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 70},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                            "impact": {"type": "string", "maxLength": 90},
                        },
                        "required": ["stable_id", "translated_title", "translated_summary", "impact"],
                    },
                }
            },
            "required": ["articles"],
        },
    }


def log_tool_input_preview(tool_input: Any) -> None:
    items = extract_tool_items(tool_input)
    LOG.debug(f"[anthropic] tool_use.input articles_count={len(items)}")
    for item in items:
        if not isinstance(item, dict):
            continue
        stable_id = str(item.get("stable_id") or "")
        translated_title = str(item.get("translated_title") or "").replace("\n", " ")[:80]
        translated_summary = item.get("translated_summary") or []
        if not isinstance(translated_summary, list):
            translated_summary = []
        impact = str(item.get("impact") or "").replace("\n", " ")[:80]
        log_capped(
            logging.DEBUG,
            "anthropic_tool_use_item",
            "[anthropic] tool_use.input item: "
            f"stable_id={stable_id!r}, translated_title_80={translated_title!r}, "
            f"translated_summary_count={len(translated_summary)}, impact_80={impact!r}",
        )


def extract_batch_items_from_anthropic_response(response: requests.Response) -> list:
    payload = response.json()
    content_types = response_content_types(payload)
    LOG.debug(f"[anthropic] response content types: {content_types}")
    stop_reason = payload.get("stop_reason")
    text_parts: list[str] = []
    for block in payload.get("content", []):
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == "save_ai_dev_translations":
            LOG.debug(f"[anthropic] tool_use name: {block.get('name')}")
            tool_input = block.get("input") or {}
            log_tool_input_preview(tool_input)
            items = extract_tool_items(tool_input)
            if items:
                return items
        if block.get("type") == "text" and block.get("text"):
            text_parts.append(str(block["text"]))

    content = "\n".join(text_parts)
    if not content.strip():
        exc = ValueError("No text content or usable tool input in Anthropic response")
        log_anthropic_response_failure(response, payload, content_types, stop_reason, exc)
        raise exc
    try:
        parsed = parse_ai_json(content)
    except Exception as exc:
        log_anthropic_response_failure(response, payload, content_types, stop_reason, exc)
        raise
    if isinstance(parsed, dict) and isinstance(parsed.get("articles"), list):
        return parsed["articles"]
    if isinstance(parsed, dict) and isinstance(parsed.get("translations"), list):
        return parsed["translations"]
    if isinstance(parsed, list):
        return parsed
    exc = ValueError("Anthropic batch response was not a JSON array or tool input")
    log_anthropic_response_failure(response, payload, content_types, stop_reason, exc)
    raise exc


def extract_tool_items(tool_input: Any) -> list:
    if isinstance(tool_input, list):
        return tool_input
    if not isinstance(tool_input, dict):
        return []
    for key in ("articles", "translations"):
        items = tool_input.get(key)
        if isinstance(items, list):
            return items
    return []


def log_anthropic_response_failure(
    response: requests.Response,
    payload: dict,
    content_types: list[str],
    stop_reason: str | None,
    exc: Exception,
) -> None:
    LOG.error(
        "[anthropic] response parse failure: "
        f"status_code={response.status_code}, model={payload.get('model', os.getenv('ANTHROPIC_MODEL') or DEFAULT_ANTHROPIC_MODEL)}, "
        f"content_types={content_types}, stop_reason={stop_reason}, "
        f"api_key_present={bool(os.getenv('ANTHROPIC_API_KEY'))}, "
        f"response_preview={response_preview_from_payload(payload)!r}, error={exc}"
    )


def post_anthropic_with_backoff(headers: dict[str, str], request_body: dict, model: str) -> requests.Response:
    max_attempts = 4
    for attempt in range(max_attempts):
        response = requests.post(
            ANTHROPIC_MESSAGES_ENDPOINT,
            headers=headers,
            json=request_body,
            timeout=45,
        )
        if response.status_code == 529 and attempt < max_attempts - 1:
            delay = 2**attempt
            LOG.warning(f"[anthropic] 529 overloaded; retrying in {delay}s (attempt {attempt + 1}/{max_attempts})")
            time.sleep(delay)
            continue
        try:
            response.raise_for_status()
            return response
        except requests.HTTPError as exc:
            log_anthropic_http_error(exc, model, headers)
            raise
    raise RuntimeError("Anthropic request failed after retries")


def log_anthropic_http_error(exc: requests.HTTPError, model: str, headers: dict[str, str]) -> None:
    response = exc.response
    status_code = response.status_code if response is not None else "unknown"
    response_url = response.url if response is not None else ANTHROPIC_MESSAGES_ENDPOINT
    header_names = ", ".join(sorted(headers.keys()))
    LOG.error(
        "[anthropic] api error: "
        f"status={status_code}, endpoint={response_url}, model={model}, "
        f"headers=[{header_names}], api_key_present={bool(os.getenv('ANTHROPIC_API_KEY'))}"
    )
    if status_code == 404:
        LOG.error(
            "[anthropic] 404 diagnostic: endpoint should be "
            f"{ANTHROPIC_MESSAGES_ENDPOINT}; check model availability/access for "
            f"{model} and required headers x-api-key, anthropic-version, content-type. "
            "API key value was not logged."
        )


def existing_translated_article(article_id_value: str) -> dict | None:
    article = existing_articles_by_id.get(article_id_value)
    if article and article.get("translated_title") and usable_ai_dev_translation(article):
        return article
    return None


def maybe_translate_ai_dev_with_haiku(
    article_id_value: str,
    title: str,
    description: str,
    category_key: str,
) -> tuple[str, list[str], str] | None:
    existing_article = existing_translated_article(article_id_value)
    if category_key == "ai_dev" and existing_article:
        translated_summary = existing_article.get("translated_summary") or existing_article.get("summary") or []
        impact = str(existing_article.get("impact") or "")
        return str(existing_article["translated_title"]), [str(x) for x in translated_summary[:3]], impact
    return None


def ai_translate_and_summarize(
    title: str,
    description: str,
    category_key: str,
    category_label: str,
    article_id_value: str,
    haiku_translation: dict[str, Any] | None = None,
) -> tuple[str, list[str], list[str], str, str]:
    if haiku_translation:
        translated_title = str(haiku_translation.get("translated_title") or title)
        translated_summary = [
            str(x)
            for x in haiku_translation.get("translated_summary", [])[:3]
            if str(x).strip()
        ]
        impact = str(haiku_translation.get("impact") or "")
        candidate_translation = {
            "translated_title": translated_title,
            "translated_summary": translated_summary,
            "impact": impact,
            "original_title": title,
        }
        if not usable_ai_dev_translation(candidate_translation):
            log_capped(
                logging.WARNING,
                "anthropic_save_validation_fallback",
                f"[anthropic] save validation fallback: article_id={article_id_value}",
            )
            translated_title, summary, impact = article_level_ai_dev_fallback(title, description)
            return translated_title, summary, summary, impact, ""
        summary = translated_summary if translated_summary else [description or title]
        while len(summary) < 3:
            summary.append("")
        if not impact:
            impact = "自社向けAIワークフロー設計やニュースアプリの自動化改善に応用余地があります。"
        return translated_title, summary[:3], translated_summary[:3], impact, ""

    existing_translation = maybe_translate_ai_dev_with_haiku(
        article_id_value,
        title,
        description,
        category_key,
    )
    if existing_translation:
        translated_title, translated_summary, impact = existing_translation
        summary = translated_summary if translated_summary else [description or title]
        while len(summary) < 3:
            summary.append("")
        if not impact:
            impact = "自社向けAIワークフロー設計やニュースアプリの自動化改善に応用余地があります。"
        return translated_title, summary[:3], translated_summary[:3], impact, ""

    if category_key == "ai_dev":
        _, summary, impact = article_level_ai_dev_fallback(title, description)
        return title, summary, [], impact, ""

    summary, impact, egg_insight = fallback_summary(title, description, category_label)
    return title, summary, [], impact, egg_insight


def normalize_entry(
    entry: dict,
    source: dict,
    category_key: str,
    category_label: str,
    haiku_translations: dict[str, dict[str, Any]] | None = None,
) -> dict | None:
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
        (haiku_translations or {}).get(article_id_value),
    )
    source_type = source.get("source_type", "rss")
    article = {
        "id": article_id_value,
        "title": translated_title,
        "original_title": original_title,
        "display_title": translated_title,
        "translated_title": translated_title,
        "translated_summary": translated_summary,
        "fallback_title": "",
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
    if category_key == "ai_dev" and not usable_ai_dev_translation(article):
        article["title"] = original_title
        article["display_title"] = original_title
        article["translated_title"] = ""
        article["translated_summary"] = []
        article["fallback_title"] = ai_dev_fallback_title(original_title)
    has_batch_translation = bool(haiku_translations and article_id_value in haiku_translations)
    if category_key == "ai_dev" and has_batch_translation and not usable_ai_dev_translation(article):
        log_capped(
            logging.WARNING,
            "ai_dev_fallback_before_save",
            f"[validation] ai_dev fallback before save: article_id={article_id_value}",
        )
        _, summary, impact = article_level_ai_dev_fallback(original_title, description)
        article["title"] = original_title
        article["display_title"] = original_title
        article["translated_title"] = ""
        article["translated_summary"] = summary
        article["summary"] = summary
        article["impact"] = impact
        article["fallback_title"] = ai_dev_fallback_title(original_title)
    return article


def batch_translate_ai_dev_entries(entries: list[dict], category_key: str) -> dict[str, dict[str, Any]]:
    global anthropic_batch_requested
    global anthropic_translation_count
    global anthropic_last_generic_translation_count
    global anthropic_last_matched_count
    global anthropic_last_response_count

    if category_key != "ai_dev":
        return {}
    if anthropic_batch_requested:
        return {}
    if not os.getenv("ANTHROPIC_API_KEY"):
        return {}

    candidates: list[dict[str, str]] = []
    stable_to_article_id: dict[str, str] = {}
    for entry in entries:
        original_title = clean_text(entry.get("title", ""))
        url = entry.get("link", "")
        if not original_title or not url:
            continue
        description = clean_text(entry.get("summary", "") or entry.get("description", ""))
        article_id_value = article_id(url, original_title)
        if existing_translated_article(article_id_value):
            continue
        if not is_english_article(original_title, description):
            continue
        stable_id = f"ai_dev_{len(candidates)}"
        stable_to_article_id[stable_id] = article_id_value
        candidates.append(
            {
                "stable_id": stable_id,
                "id": article_id_value,
                "title": original_title,
                "description": description,
            }
        )
        if len(candidates) >= ANTHROPIC_TRANSLATION_LIMIT:
            break

    if not candidates:
        return {}

    anthropic_batch_requested = True
    try:
        stable_translations = call_anthropic_haiku_batch(candidates)
        translations = {
            stable_to_article_id[stable_id]: translation
            for stable_id, translation in stable_translations.items()
            if stable_id in stable_to_article_id
        }
        response_count = anthropic_last_response_count
        matched_count = anthropic_last_matched_count
        meaningful_translation_count = len(translations)
        generic_translation_count = anthropic_last_generic_translation_count
        unmatched_count = max(0, response_count - matched_count)
        fallback_count = len(candidates) - meaningful_translation_count
        anthropic_translation_count = meaningful_translation_count
        LOG.info(
            "[anthropic] ai_dev batch translated "
            f"{anthropic_translation_count}/{len(candidates)} requested articles"
        )
        LOG.info(
            "[anthropic] ai_dev stable_id match: "
            f"requested_count={len(candidates)}, response_count={response_count}, "
            f"matched_count={matched_count}, unmatched_count={unmatched_count}, fallback_count={fallback_count}"
        )
        LOG.info(
            "[anthropic] ai_dev batch totals: "
            f"api_success=1, matched_count={matched_count}, "
            f"meaningful_translation_count={meaningful_translation_count}, "
            f"generic_translation_count={generic_translation_count}, "
            f"fallback_count={fallback_count}"
        )
        return translations
    except Exception as exc:
        LOG.error(f"[anthropic] ai_dev batch unavailable: {exc}")
        LOG.info(
            "[anthropic] ai_dev stable_id match: "
            f"requested_count={len(candidates)}, response_count=0, matched_count=0, "
            f"unmatched_count=0, fallback_count={len(candidates)}"
        )
        LOG.info(
            "[anthropic] ai_dev batch totals: "
            f"api_success=0, matched_count=0, meaningful_translation_count=0, "
            f"generic_translation_count=0, fallback_count={len(candidates)}"
        )
        return {}


def fetch_source(source: dict, category_key: str, category_label: str) -> list[dict]:
    source_type = source.get("source_type", "rss")
    collector = COLLECTORS.get(source_type)
    if collector is None:
        LOG.warning(f"[source] {category_key} / {source['name']}: unsupported source_type={source_type}")
        return []
    entries = collector(source)
    articles = []
    for entry in entries:
        article = normalize_entry(entry, source, category_key, category_label)
        if article:
            articles.append(article)
    return articles


def provisional_display_articles(articles: list[dict]) -> list[dict]:
    prefs = load_yaml(PREFERENCES_PATH)
    feedback = load_json(FEEDBACK_PATH, {})
    for article in articles:
        article["score"] = score_article(article, prefs, feedback)
    return enforce_category_limits(articles, 10)


def ai_dev_display_articles(articles: list[dict]) -> list[dict]:
    return [
        article
        for article in sorted(articles, key=lambda x: x.get("score", 0), reverse=True)
        if article.get("category") == "ai_dev"
    ][:10]


def log_title_list(label: str, titles: list[str]) -> None:
    log_safe(f"[anthropic] {label}={json.dumps(titles, ensure_ascii=False)}", logging.DEBUG)


def log_value_list(label: str, values: list[str]) -> None:
    log_safe(f"[anthropic] {label}={json.dumps(values, ensure_ascii=False)}", logging.DEBUG)


def select_final_ai_dev_translation_candidates(articles: list[dict]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    display_articles = provisional_display_articles(articles)
    ai_dev_articles = ai_dev_display_articles(display_articles)
    japanese_source_count = 0
    for article in ai_dev_articles:
        original_title = clean_text(str(article.get("original_title") or article.get("title") or ""))
        description = clean_text(str(article.get("raw_summary") or ""))
        if not original_title or not article.get("id"):
            continue
        if is_japanese_article(original_title, description):
            japanese_source_count += 1
            continue
        if not is_english_article(original_title, description):
            continue
        stable_id = f"ai_dev_{len(candidates)}"
        candidates.append(
            {
                "stable_id": stable_id,
                "id": str(article["id"]),
                "title": original_title,
                "description": description,
            }
        )
    RUN_STATS["ai_translation"]["source_japanese_count"] = japanese_source_count
    RUN_STATS["ai_translation"]["source_english_count"] = len(candidates)
    first_title = candidates[0]["title"] if candidates else ""
    log_title_list("translation_request_titles", [candidate["title"] for candidate in candidates[:ANTHROPIC_TRANSLATION_LIMIT]])
    log_value_list("translation_request_article_ids", [candidate["id"] for candidate in candidates[:ANTHROPIC_TRANSLATION_LIMIT]])
    LOG.info(
        "[anthropic] ai_dev final translation candidates: "
        f"candidate_count={len(ai_dev_articles)}, "
        f"source_japanese_count={japanese_source_count}, "
        f"source_english_count={len(candidates)}, "
        f"request_article_count={min(len(candidates), ANTHROPIC_TRANSLATION_LIMIT)}, "
        f"first_article_title={console_safe(first_title[:160])!r}"
    )
    return candidates[:ANTHROPIC_TRANSLATION_LIMIT]


def ai_dev_japanese_passthrough_summary(title: str, description: str) -> tuple[list[str], str]:
    title_hint = clean_text(title)[:90]
    body_hint = clean_text(description)[:90]
    if not body_hint:
        body_hint = title_hint
    summary = [
        f"日本語原文記事です。主題は「{title_hint}」です。"[:120],
        f"本文の手がかり: {body_hint}"[:120],
        "AI開発・ツール運用・プロダクト判断に関係する論点として確認します。",
    ]
    impact = f"「{title_hint[:42]}」はAI活用や開発運用の優先度判断に使える具体事例です。"[:120]
    return summary, impact


def ensure_ai_dev_japanese_display_articles_localized(articles: list[dict]) -> int:
    display_articles = provisional_display_articles(articles)
    localized_count = 0
    for article in ai_dev_display_articles(display_articles):
        original_title = clean_text(str(article.get("original_title") or article.get("title") or ""))
        description = clean_text(str(article.get("raw_summary") or ""))
        if not original_title or article.get("source_type") == "fallback":
            continue
        if not is_japanese_article(original_title, description):
            continue
        summary, impact = ai_dev_japanese_passthrough_summary(original_title, description)
        article["title"] = original_title
        article["display_title"] = original_title
        article["translated_title"] = original_title
        article["translated_summary"] = summary
        article["summary"] = summary
        article["impact"] = impact
        article["fallback_title"] = ""
        localized_count += 1
        log_capped(
            logging.DEBUG,
            "ai_dev_japanese_passthrough",
            "[anthropic] ai_dev japanese passthrough: "
            f"article_id={article.get('id')}, translated_summary_count={len(summary)}, "
            f"title_80={console_safe(original_title[:80])!r}",
        )
    RUN_STATS["ai_translation"]["japanese_passthrough_count"] = localized_count
    return localized_count


def apply_ai_dev_translation(article: dict, translation: dict[str, Any]) -> None:
    translated_title = str(translation.get("translated_title") or article.get("translated_title") or "")
    translated_summary = [
        str(x)
        for x in translation.get("translated_summary", [])[:3]
        if str(x).strip()
    ]
    impact = str(translation.get("impact") or article.get("impact") or "")
    candidate_translation = {
        "translated_title": translated_title,
        "translated_summary": translated_summary,
        "impact": impact,
        "original_title": str(article.get("original_title") or article.get("title") or ""),
    }
    if not usable_ai_dev_translation(candidate_translation):
        log_capped(
            logging.WARNING,
            "anthropic_final_save_validation_fallback",
            f"[anthropic] final save validation fallback: article_id={article.get('id')}",
        )
        _, translated_summary, impact = article_level_ai_dev_fallback(
            str(article.get("original_title") or article.get("title") or ""),
            str(article.get("raw_summary") or ""),
        )
        original_title = str(article.get("original_title") or article.get("title") or "")
        article["title"] = original_title
        article["display_title"] = original_title
        article["translated_title"] = ""
        article["translated_summary"] = []
        article["summary"] = translated_summary[:3]
        article["impact"] = impact
        article["fallback_title"] = ai_dev_fallback_title(original_title)
        return
    article["title"] = translated_title
    article["display_title"] = translated_title
    article["translated_title"] = translated_title
    article["translated_summary"] = translated_summary[:3]
    article["summary"] = translated_summary[:3]
    article["impact"] = impact
    article["fallback_title"] = ""
    log_capped(
        logging.DEBUG,
        "ai_dev_applied_translation",
        "[anthropic] applied translation to article: "
        f"article_id={article.get('id')}, translated_title_exists={bool(article.get('translated_title'))}, "
        f"translated_summary_exists={bool(article.get('translated_summary'))}, "
        f"impact_exists={bool(article.get('impact'))}",
    )


def log_final_ai_dev_display_status(articles: list[dict], requested_article_ids: set[str] | None = None) -> None:
    display_articles = provisional_display_articles(articles)
    ai_dev_articles = ai_dev_display_articles(display_articles)
    display_article_ids = [str(article.get("id") or "") for article in ai_dev_articles]
    translated_count = sum(
        1
        for article in ai_dev_articles
        if article.get("source_type") != "fallback" and usable_ai_dev_translation(article)
    )
    untranslated_count = len(ai_dev_articles) - translated_count
    requested_article_ids = requested_article_ids or set()
    request_display_match_count = len(set(display_article_ids) & requested_article_ids)
    RUN_STATS["ai_translation"]["final_display_translated_count"] = translated_count
    RUN_STATS["ai_translation"]["final_display_untranslated_count"] = untranslated_count
    RUN_STATS["ai_translation"]["request_display_match_count"] = request_display_match_count
    log_value_list("final_ai_dev_display_article_ids", display_article_ids)
    LOG.info(
        "[anthropic] ai_dev request/display id match: "
        f"request_display_match_count={request_display_match_count}, "
        f"request_article_count={len(requested_article_ids)}, "
        f"display_article_count={len(display_article_ids)}"
    )
    LOG.info(
        "[anthropic] ai_dev display translation coverage: "
        f"translated_display_count={translated_count}, "
        f"untranslated_display_count={untranslated_count}"
    )


def log_ai_dev_save_readiness(articles: list[dict]) -> None:
    display_articles = provisional_display_articles(articles)
    for article in ai_dev_display_articles(display_articles):
        log_capped(
            logging.DEBUG,
            "ai_dev_save_readiness",
            str(
                {
                    "article_id": article["id"],
                    "translated_title_exists": bool(article.get("translated_title")),
                    "translated_summary_exists": bool(article.get("translated_summary")),
                    "impact_exists": bool(article.get("impact")),
                    "translation_usable": article.get("source_type") != "fallback"
                    and usable_ai_dev_translation(article),
                }
            ),
        )


def call_anthropic_with_chunk_retry(candidates: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    try:
        return call_anthropic_haiku_batch(candidates)
    except Exception as exc:
        if len(candidates) <= 5:
            raise
        LOG.warning(f"[anthropic] ai_dev full batch failed; retrying in chunks of 5: {exc}")
    translations: dict[str, dict[str, Any]] = {}
    for index in range(0, len(candidates), 5):
        chunk = candidates[index : index + 5]
        LOG.info(
            "[anthropic] ai_dev chunk retry: "
            f"chunk_start={index}, chunk_size={len(chunk)}"
        )
        translations.update(call_anthropic_haiku_batch(chunk))
    return translations


def translate_final_ai_dev_articles(articles: list[dict]) -> None:
    global anthropic_batch_requested

    ensure_ai_dev_japanese_display_articles_localized(articles)
    candidates = select_final_ai_dev_translation_candidates(articles)
    requested_article_ids = {candidate["id"] for candidate in candidates}
    RUN_STATS["ai_translation"]["api_key_present"] = bool(os.getenv("ANTHROPIC_API_KEY"))
    RUN_STATS["ai_translation"]["model"] = os.getenv("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    RUN_STATS["ai_translation"]["request_count"] = len(candidates)
    if not candidates:
        log_final_ai_dev_display_status(articles, requested_article_ids)
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        RUN_STATS["ai_translation"].update(
            {
                "api_success": 0,
                "response_count": 0,
                "matched_count": 0,
                "meaningful_translation_count": 0,
                "generic_translation_count": 0,
                "fallback_count": len(candidates),
            }
        )
        log_final_ai_dev_display_status(articles, requested_article_ids)
        return
    anthropic_batch_requested = True
    stable_to_article_id = {candidate["stable_id"]: candidate["id"] for candidate in candidates}
    try:
        stable_translations = call_anthropic_with_chunk_retry(candidates)
    except Exception as exc:
        LOG.error(f"[anthropic] ai_dev final batch unavailable: {exc}")
        LOG.info(
            "[anthropic] ai_dev batch totals: "
            f"api_success=0, matched_count=0, meaningful_translation_count=0, "
            f"generic_translation_count=0, fallback_count={len(candidates)}"
        )
        RUN_STATS["ai_translation"].update(
            {
                "api_success": 0,
                "response_count": 0,
                "matched_count": 0,
                "meaningful_translation_count": 0,
                "generic_translation_count": 0,
                "fallback_count": len(candidates),
            }
        )
        log_final_ai_dev_display_status(articles, requested_article_ids)
        return

    translations = {
        stable_to_article_id[stable_id]: translation
        for stable_id, translation in stable_translations.items()
        if stable_id in stable_to_article_id
    }
    response_count = max(anthropic_last_response_count, len(stable_translations))
    matched_count = max(anthropic_last_matched_count, len(stable_translations))
    meaningful_translation_count = len(translations)
    generic_translation_count = max(0, matched_count - meaningful_translation_count)
    unmatched_count = max(0, response_count - matched_count)
    fallback_count = len(candidates) - meaningful_translation_count
    RUN_STATS["ai_translation"].update(
        {
            "api_success": 1,
            "response_count": response_count,
            "matched_count": matched_count,
            "meaningful_translation_count": meaningful_translation_count,
            "generic_translation_count": generic_translation_count,
            "fallback_count": fallback_count,
        }
    )
    LOG.info(
        "[anthropic] ai_dev stable_id match: "
        f"requested_count={len(candidates)}, response_count={response_count}, "
        f"matched_count={matched_count}, unmatched_count={unmatched_count}, fallback_count={fallback_count}"
    )
    LOG.info(
        "[anthropic] ai_dev batch totals: "
        f"api_success=1, matched_count={matched_count}, "
        f"meaningful_translation_count={meaningful_translation_count}, "
        f"generic_translation_count={generic_translation_count}, "
        f"fallback_count={fallback_count}"
    )
    for article in articles:
        if article.get("category") != "ai_dev":
            continue
        translation = translations.get(str(article.get("id")))
        if translation:
            apply_ai_dev_translation(article, translation)
    log_final_ai_dev_display_status(articles, requested_article_ids)


def print_fetch_run_summary(articles: list[dict]) -> None:
    display_articles = provisional_display_articles(articles)
    fetched_counts: dict[str, int] = {}
    for result in RUN_STATS["rss_sources"]:
        if result.get("failed_reason"):
            continue
        category = str(result["category"])
        fetched_counts[category] = fetched_counts.get(category, 0) + int(result.get("fetched_count", 0))
    displayed_counts = count_by_category(display_articles)
    fallback_counts = {
        category: int(RUN_STATS["fallback_by_category"].get(category, 0))
        for category in sorted({*fetched_counts.keys(), *displayed_counts.keys(), *RUN_STATS["fallback_by_category"].keys()})
    }

    LOG.info("=== Personal Newsroom Run Summary ===")
    for category in ("business", "food", "ai_dev", "egg"):
        LOG.info(
            f"{category}: fetched={fetched_counts.get(category, 0)}, "
            f"displayed={displayed_counts.get(category, 0)}, "
            f"fallback={fallback_counts.get(category, 0)}"
        )

    LOG.info("RSS failures:")
    failures = [result for result in RUN_STATS["rss_sources"] if result.get("failed_reason")]
    if failures:
        for result in failures:
            LOG.info(f"- {result['source']}: {result['failed_reason']}")
    else:
        LOG.info("- none")

    zero_sources = [result for result in RUN_STATS["rss_sources"] if not result.get("failed_reason") and result.get("fetched_count") == 0]
    if zero_sources:
        LOG.info("RSS zero_count_sources:")
        for result in zero_sources:
            LOG.info(f"- {result['category']} / {result['source']} / {result['source_type']}")

    ai = RUN_STATS["ai_translation"]
    LOG.info("AI translation:")
    for key in AI_TRANSLATION_SUMMARY_KEYS:
        LOG.info(f"{key}={ai[key]}")


def filter_category_articles(category_key: str, articles: list[dict]) -> list[dict]:
    if category_key != "egg":
        return articles
    relevant = [article for article in articles if egg_article_is_relevant(article)]
    removed_count = len(articles) - len(relevant)
    if removed_count:
        LOG.info(
            "[category_filter] egg relevance: "
            f"kept={len(relevant)}, removed={removed_count}, input={len(articles)}"
        )
    return relevant


def main() -> None:
    sources = normalized_categories(load_yaml(SOURCES_PATH))
    all_articles: list[dict] = []
    seen: set[str] = set()
    for category_key, category in sources.items():
        category_articles: list[dict] = []
        for source in category.get("sources", []):
            try:
                source_articles = fetch_source(source, category_key, category["label"])
                record_source_result(category_key, source, len(source_articles))
                category_articles.extend(source_articles)
            except Exception as exc:
                record_source_result(category_key, source, 0, summarize_exception(exc))
                continue
        category_articles = filter_category_articles(category_key, category_articles)
        if len(category_articles) < 10:
            missing = 10 - len(category_articles)
            LOG.warning(f"[fallback] {category_key} / {category['label']}: adding {missing} sample articles")
            RUN_STATS["fallback_by_category"][category_key] = RUN_STATS["fallback_by_category"].get(category_key, 0) + missing
            category_articles.extend(sample_articles(category_key, category["label"], missing))
        for article in category_articles:
            seen_key = f"{article['category']}:{article['id']}"
            if seen_key in seen:
                continue
            seen.add(seen_key)
            all_articles.append(article)

    translate_final_ai_dev_articles(all_articles)
    log_ai_dev_save_readiness(all_articles)
    print_fetch_run_summary(all_articles)

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(all_articles, ensure_ascii=False, indent=2), encoding="utf-8")
    log_suppression_summary()
    LOG.info(f"Wrote {len(all_articles)} articles to {DATA_PATH}")


if __name__ == "__main__":
    main()
