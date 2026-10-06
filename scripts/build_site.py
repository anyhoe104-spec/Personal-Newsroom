from __future__ import annotations

import json
import hashlib
import re
import logging
from datetime import datetime, timezone

import yaml
from pathlib import Path

from newsroom_config import config_path, state_path
from newsroom_logging import get_logger, log_capped, log_suppression_summary


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_PATH = state_path("articles.json")
PUBLIC_DIR = ROOT / "public"
INDEX_PATH = PUBLIC_DIR / "index.html"
LOG = get_logger()



def embed_json(payload: dict) -> str:
    """HTMLの<script>ブロックへ安全に埋め込めるJSON文字列を返す。

    記事のタイトルや要約は外部RSS由来で、内容を制御できない。素の
    json.dumps はJSONとしては正しくエスケープするが `</script>` を
    無害化しないため、そのまま埋め込むとscript要素がそこで終了し、
    以降がHTMLとして解釈されてしまう（記事1本で全体が壊れ、任意の
    マークアップを注入されうる）。

    JSON仕様上 `<` と `\u003c` は等価なので、`JSON.parse` の結果は
    変わらないまま、HTMLパーサからは `</script>` が見えなくなる。
    """
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")

def load_articles() -> list[dict]:
    if not ARTICLES_PATH.exists():
        return []
    return json.loads(ARTICLES_PATH.read_text(encoding="utf-8"))


def count_by_category(articles: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for article in articles:
        category = str(article.get("category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def translation_usable(article: dict) -> bool:
    if article.get("source_type") == "fallback" or article.get("fallback_title"):
        return False
    translated_summary = [line for line in article.get("translated_summary", []) if str(line).strip()]
    return bool(article.get("translated_title") and len(translated_summary) == 3 and article.get("impact"))


def reader_vocabulary(articles: list[dict]) -> dict:
    preferences = yaml.safe_load(config_path("preferences.yaml").read_text(encoding="utf-8")) or {}
    learned_path = state_path("learned.yaml")
    learned = (yaml.safe_load(learned_path.read_text(encoding="utf-8")) or {}) if learned_path.exists() else {}
    derived = learned.get("categories", {})
    # Match learning.js tokens(): vocabulary must already occur in the same
    # category's public article text. Never expose unused editorial/learned terms.
    text_by_category: dict[str, list[str]] = {}
    for article in articles:
        text = " ".join([
            article.get("title") or "", article.get("translated_title") or "",
            article.get("raw_summary") or "", " ".join(article.get("summary") or []),
        ]).lower()
        text_by_category.setdefault(article.get("category"), []).append(text)
    vocabulary = {}
    for key, value in preferences.get("categories", {}).items():
        candidates = value.get("boost_keywords", []) + list(
            derived.get(key, value).get("learned_tags", {})
        )
        vocabulary[key] = list(dict.fromkeys(
            word for word in candidates
            if isinstance(word, str) and len(word) >= 2
            and any(word.lower() in text for text in text_by_category.get(key, []))
        ))
    return vocabulary



def shell_digest(directory: Path) -> str:
    # Daily news is network-first and must not invalidate all static assets.
    names = ("app.js", "learning.js", "i18n.js", "style.css", "pwa.js",
             "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png")
    return hashlib.sha256(b"".join((directory / name).read_bytes() for name in names)).hexdigest()[:16]


def main() -> None:
    articles = load_articles()
    display_counts = count_by_category(articles)
    for category in ("business", "food", "ai_dev", "egg"):
        LOG.info(f"[display_summary] {category}: displayed={display_counts.get(category, 0)}")
    translation_articles = [
        article
        for article in sorted(
            [article for article in articles if article.get("category") in {"ai_dev", "egg"}],
            key=lambda item: item.get("score", 0),
            reverse=True,
        )[:20]
    ]
    for article in translation_articles:
        log_capped(
            logging.DEBUG,
            "build_translation_article",
            str(
                {
                    "build_article_id": article.get("id"),
                    "category": article.get("category"),
                    "translated_title_exists": bool(article.get("translated_title")),
                    "translated_summary_exists": bool(article.get("translated_summary")),
                    "impact_exists": bool(article.get("impact")),
                    "translation_usable": translation_usable(article),
                }
            ),
            limit=20,
        )
    translated_articles = sum(
        1
        for article in translation_articles
        if translation_usable(article)
    )
    LOG.info("=== Personal Newsroom Build Summary ===")
    for category in ("business", "food", "ai_dev", "egg"):
        LOG.info(f"{category}: displayed={display_counts.get(category, 0)}")
    LOG.info(
        "Translation render check: "
        f"final_display_translated_count={translated_articles}, "
        f"final_display_untranslated_count={len(translation_articles) - translated_articles}"
    )
    category_order = ["business", "food", "ai_dev", "egg"]
    categories = {
        key: next(
            (a.get("category_label") or key for a in articles if a.get("category") == key),
            key,
        )
        for key in category_order
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "vocabulary": reader_vocabulary(articles),
        "categories": categories,
        "articles": articles,
    }
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title data-i18n="app.title">Personal-Newsroom</title>
  <meta name="theme-color" content="#123e35">
  <meta name="description" content="ニュースを評価して、あなたの関心に育てるパーソナルニュースルーム。">
  <link rel="apple-touch-icon" href="./icon-192.png">
  <link rel="manifest" href="./manifest.webmanifest">
  <link rel="icon" href="./icon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="./style.css">
</head>
<body>
  <a class="skip-link" href="#app">記事一覧へ</a>
  <header class="app-header">
    <a class="brand" href="./"><span class="brand-mark" aria-hidden="true">N.</span><span>PERSONAL<br>NEWSROOM</span></a>
    <button id="openSettings" class="settings-button" type="button" data-i18n="reader.settings">設定</button>
  </header>
  <div class="page-shell">
    <section class="hero">
      <p class="eyebrow">YOUR DAILY PERSPECTIVE</p>
      <h1 data-i18n="header.headline">今日の視点を、育てる。</h1>
      <p class="intro" data-i18n="reader.intro">読む。選ぶ。自分の視点が育つ。</p>
      <p class="updated"><span data-i18n="header.updated_label">更新:</span> <time id="generatedAt"></time></p>
      <p id="learningCount" class="learning-count"></p>
    </section>
    <p id="offline" class="banner" hidden data-i18n="reader.offline">オフラインです。</p>
    <p id="freshness" class="banner" hidden data-i18n="reader.freshness">記事の日付をご確認ください。</p>
    <div class="section-heading"><h2 id="viewTitle"></h2><p id="resultCount" role="status"></p></div>
    <div class="category-nav"><p class="category-caption" data-i18n="reader.category_filter"></p><nav class="tabs" id="tabs" aria-label="カテゴリ" data-i18n-attr="aria-label:nav.categories_aria_label"></nav></div>
    <section id="filters" class="filters" aria-label="記事の絞り込み">
      <label class="search-box"><span class="sr-only" data-i18n="reader.search">記事・情報源を検索</span><input id="search" type="search" placeholder="記事・情報源を検索" data-i18n-attr="placeholder:reader.search" autocomplete="off"></label>
      <label class="sort-label"><span class="sr-only" data-i18n="reader.sort">表示順</span><select id="sort"><option value="recommended" data-i18n="reader.recommended">おすすめ順</option><option value="latest" data-i18n="reader.latest">新しい順</option></select></label>
      <label class="check-label"><input id="unread" type="checkbox"><span data-i18n="reader.unread">未読のみ</span></label>
      <button id="refreshRanking" type="button" data-i18n="reader.refresh_ranking"></button>
    </section>
    <p id="rankingHint" class="muted ranking-hint"></p>
    <main id="app" class="article-list" tabindex="-1"></main>
  </div>
  <nav class="bottom-nav" aria-label="メインメニュー">
    <button type="button" data-view="today"><span aria-hidden="true">▤</span><span data-i18n="reader.view_today">今日のニュース</span></button>
    <button type="button" data-view="saved"><span aria-hidden="true">◇</span><span data-i18n="reader.view_saved">あとで読む</span></button>
    <button type="button" data-view="history"><span aria-hidden="true">◷</span><span data-i18n="reader.view_history">評価の履歴</span></button>
    <button type="button" data-view="insights"><span aria-hidden="true">✧</span><span data-i18n="reader.view_insights">あなたの関心</span></button>
  </nav>
  <p id="feedbackStatus" class="toast" role="status" aria-live="polite"></p>
  <dialog id="settings" aria-labelledby="settingsTitle">
    <div class="dialog-heading"><h2 id="settingsTitle" data-i18n="reader.settings">設定</h2><button id="closeSettings" type="button" data-i18n="reader.close">閉じる</button></div>
    <p id="settingsStatus" role="status" aria-live="polite"></p>
    <p data-i18n="reader.privacy"></p>
    <label class="setting-row"><span data-i18n="reader.learning"></span><input id="learningToggle" type="checkbox"></label>
    <label class="setting-row"><span data-i18n="reader.compact"></span><input id="compactToggle" type="checkbox"></label>
    <label class="setting-row"><span data-i18n="reader.theme"></span><select id="theme"><option value="system" data-i18n="reader.system"></option><option value="light" data-i18n="reader.light"></option><option value="dark" data-i18n="reader.dark"></option></select></label>
    <p data-i18n="reader.tag_note"></p>
    <h3 data-i18n="reader.data"></h3>
    <div class="data-actions"><button id="downloadBackup" type="button" data-i18n="reader.backup"></button><label class="import-label"><span data-i18n="reader.import"></span><input id="importBackup" type="file" aria-describedby="importHelp"></label><p id="importHelp" data-i18n="reader.import_help"></p></div>
    <details><summary data-i18n="reader.paste_backup"></summary><label for="backupText" data-i18n="reader.paste_help"></label><textarea id="backupText" rows="6" spellcheck="false" autocomplete="off"></textarea><button id="importPastedBackup" type="button" data-i18n="reader.import_pasted"></button></details>
    <details><summary data-i18n="reader.advanced"></summary><div class="data-actions"><button id="copyFeedback" type="button" data-i18n="feedback_tools.copy"></button><button id="downloadFeedback" type="button" data-i18n="feedback_tools.download"></button></div></details>
    <p data-i18n="reader.install_hint"></p><button id="installApp" type="button" hidden data-i18n="reader.install"></button>
    <button id="resetData" class="danger" type="button" data-i18n="reader.reset"></button>
  </dialog>
  <noscript><p>記事の表示にはJavaScriptが必要です。ブラウザでJavaScriptを有効にしてください。</p></noscript>

  <script id="newsData" type="application/json">{embed_json(payload)}</script>
  <script src="./i18n.js"></script>
  <script src="./learning.js"></script>
  <script src="./app.js"></script>
  <script src="./pwa.js"></script>
</body>
</html>
"""
    INDEX_PATH.write_text(html, encoding="utf-8")
    worker = PUBLIC_DIR / "sw.js"
    if worker.exists():
        digest = shell_digest(PUBLIC_DIR)
        worker.write_text(re.sub(r"newsroom-shell-[a-z0-9]+", f"newsroom-shell-{digest}", worker.read_text(encoding="utf-8")), encoding="utf-8")
    log_suppression_summary()
    LOG.info(f"Built {INDEX_PATH}")


if __name__ == "__main__":
    main()
