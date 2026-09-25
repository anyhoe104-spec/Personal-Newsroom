import json
import logging
import os
import re
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import analyze_source_feedback  # noqa: E402
import build_site  # noqa: E402
import fetch_rss  # noqa: E402
import newsroom_config  # noqa: E402
import newsroom_logging  # noqa: E402
import score_articles  # noqa: E402
import validate_newsroom  # noqa: E402


def article(article_id: str, category: str, **overrides) -> dict:
    item = {
        "id": article_id,
        "category": category,
        "title": f"Article {article_id}",
        "original_title": "",
        "raw_summary": "",
        "source": "source-a",
        "source_type": "rss",
        "score": 50,
        "url": f"https://example.com/{article_id}",
    }
    item.update(overrides)
    return item


class ScoringRegressionTests(unittest.TestCase):
    def test_ai_technical_article_outranks_commerce_article(self):
        technical = article(
            "technical",
            "ai_dev",
            title="LLM agent API evaluation workflow for developers",
        )
        commerce = article(
            "commerce",
            "ai_dev",
            title="Kindle book sale coupon campaign",
        )

        self.assertGreater(
            score_articles.category_quality_adjustment(technical),
            score_articles.category_quality_adjustment(commerce),
        )

    def test_fallback_score_is_capped(self):
        fallback = article("fallback", "business", source_type="fallback")
        prefs = {
            "categories": {"business": {"boost_keywords": [], "downrank_keywords": []}},
            "preferred_sources": {"business": ["source-a"]},
            "scoring": {
                "keyword_weight": 0.0,
                "source_weight": 1.0,
                "recency_weight": 0.0,
                "feedback_weight": 0.0,
            },
        }

        self.assertEqual(score_articles.score_article(fallback, prefs, {}), 25.0)

    def test_ai_source_limit_applies_when_alternatives_exist(self):
        items = [article(f"a-{i}", "ai_dev", source="source-a", score=100 - i) for i in range(6)]
        items.extend(
            article(f"b-{i}", "ai_dev", source=f"source-{i}", score=80 - i)
            for i in range(6)
        )

        selected = score_articles.select_category_articles("ai_dev", items, 10, set())

        self.assertEqual(len(selected), 10)
        self.assertLessEqual(sum(item["source"] == "source-a" for item in selected), 4)

    def test_cross_category_duplicate_is_suppressed(self):
        shared_url = "https://example.com/shared"
        items = [
            article("business-1", "business", url=shared_url, score=90),
            article("ai-1", "ai_dev", url=shared_url, score=95),
            article("ai-2", "ai_dev", score=80),
        ]

        selected = score_articles.enforce_category_limits(items, per_category=2)

        self.assertEqual(sum(item["url"] == shared_url for item in selected), 1)
        self.assertIn("business-1", {item["id"] for item in selected})

    def test_borderline_egg_development_article_is_kept(self):
        item = article(
            "egg-borderline",
            "egg",
            title="食品工場の製造技術と品質管理",
            raw_summary="食品産業の加工技術と製造工程を解説する",
        )

        self.assertGreaterEqual(score_articles.egg_article_relevance(item), 0.45)
        self.assertTrue(score_articles.egg_article_is_relevant(item))


class TranslationRegressionTests(unittest.TestCase):
    def test_specific_japanese_translation_is_usable(self):
        item = {
            "original_title": "OpenAI launches a new Codex workflow",
            "translated_title": "OpenAIが新しいCodexワークフローを公開",
            "translated_summary": [
                "OpenAIが開発作業向けの新機能を公開した",
                "Codexによる実装と確認の流れを効率化する",
                "開発チームの反復作業を短縮できる",
            ],
            "impact": "ニュース収集基盤の開発手順を自動化する際の参考になる。",
        }

        self.assertTrue(fetch_rss.usable_ai_dev_translation(item))

    def test_generic_translation_title_is_rejected(self):
        item = {
            "original_title": "OpenAI launches a new Codex workflow",
            "translated_title": "AI・開発ニュースの注目アップデート",
            "translated_summary": ["要点その一", "要点その二", "要点その三"],
            "impact": "開発作業の具体的な自動化方法を検討する材料になる。",
        }

        self.assertFalse(fetch_rss.usable_ai_dev_translation(item))

    def test_english_summary_is_rejected(self):
        self.assertTrue(
            fetch_rss.looks_like_untranslated_summary(
                ["This is an English summary", "Developer workflow update", "Read the article"]
            )
        )

    def test_japanese_display_article_gets_localized_fields(self):
        item = article(
            "jp-1",
            "ai_dev",
            title="生成AIを使った開発ワークフローの改善",
            original_title="生成AIを使った開発ワークフローの改善",
            raw_summary="開発チームが生成AIを導入した事例を紹介します。",
            translated_title="",
            translated_summary=[],
            summary=[],
            impact="",
        )

        count = fetch_rss.ensure_ai_dev_japanese_display_articles_localized([item])

        self.assertEqual(count, 1)
        self.assertEqual(item["translated_title"], item["original_title"])
        self.assertEqual(len(item["translated_summary"]), 3)
        self.assertTrue(item["impact"])


class QualityMetricsRegressionTests(unittest.TestCase):
    def test_quality_metrics_report_real_rate_and_source_concentration(self):
        items = [
            article("real-1", "egg", source="source-a"),
            article("real-2", "egg", source="source-a"),
            article("fallback", "egg", source="sample", source_type="fallback"),
        ]

        metrics = validate_newsroom.category_quality_metrics(items, "egg")

        self.assertEqual(metrics["real_articles"], 2)
        self.assertAlmostEqual(metrics["real_article_rate"], 2 / 3)
        self.assertEqual(metrics["synthetic_fallback"], 1)
        self.assertEqual(metrics["localization_fallback"], 0)
        self.assertEqual(metrics["unique_sources"], 1)
        self.assertEqual(metrics["max_source_share"], 1.0)

    def test_translation_fallback_remains_a_real_article(self):
        item = article(
            "ai-real",
            "ai_dev",
            fallback_title="翻訳未取得: Original title",
        )

        metrics = validate_newsroom.category_quality_metrics([item], "ai_dev")

        self.assertEqual(metrics["real_articles"], 1)
        self.assertEqual(metrics["synthetic_fallback"], 0)
        self.assertEqual(metrics["localization_fallback"], 1)

    def test_cross_category_duplicate_metric(self):
        shared_url = "https://example.com/shared"
        items = [
            article("business", "business", url=shared_url),
            article("ai", "ai_dev", url=shared_url),
            article("egg", "egg"),
        ]

        self.assertEqual(validate_newsroom.cross_category_duplicate_count(items), 1)


class EggPriceKeywordRegressionTests(unittest.TestCase):
    def test_price_keywords_are_readable_japanese(self):
        # These were double-encoded through cp932 and could never match an article.
        for keyword in score_articles.EGG_PRICE_KEYWORDS:
            self.assertTrue(keyword.isprintable())
        self.assertIn("価格", score_articles.EGG_PRICE_KEYWORDS)
        self.assertIn("卵価", score_articles.EGG_PRICE_KEYWORDS)

    def test_price_article_is_penalised(self):
        prefs = {
            "categories": {"egg": {"boost_keywords": [], "downrank_keywords": []}},
            "preferred_sources": {"egg": []},
            "scoring": {
                "keyword_weight": 0.0,
                "source_weight": 0.0,
                "recency_weight": 0.0,
                "feedback_weight": 0.0,
                "egg_price_weight": 0.05,
            },
        }
        priced = article("priced", "egg", title="鶏卵の卵価が上昇、加工技術で商品開発を継続")
        plain = article("plain", "egg", title="鶏卵の加工技術で商品開発を継続")

        self.assertLess(
            score_articles.score_article(priced, prefs, {}),
            score_articles.score_article(plain, prefs, {}),
        )


class LoggingRegressionTests(unittest.TestCase):
    def setUp(self):
        newsroom_logging.reset_caps()
        self.logger = newsroom_logging.get_logger()
        self.records: list[logging.LogRecord] = []

        class Collector(logging.Handler):
            def emit(inner, record):
                self.records.append(record)

        self.handler = Collector(level=logging.DEBUG)
        self.logger.addHandler(self.handler)
        self.previous_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.previous_level)
        newsroom_logging.reset_caps()

    def test_log_capped_stops_after_the_limit(self):
        for index in range(12):
            newsroom_logging.log_capped(logging.DEBUG, "unit_test_group", f"line {index}", limit=3)

        messages = [record.getMessage() for record in self.records]
        self.assertEqual(messages[:3], ["line 0", "line 1", "line 2"])
        self.assertEqual(len(messages), 4)
        self.assertIn("suppressing the rest", messages[3])

    def test_suppression_summary_reports_dropped_messages(self):
        for index in range(8):
            newsroom_logging.log_capped(logging.DEBUG, "unit_test_group", f"line {index}", limit=2)
        self.records.clear()

        newsroom_logging.log_suppression_summary()

        messages = [record.getMessage() for record in self.records]
        self.assertTrue(any("emitted=2, suppressed=6" in message for message in messages))

    def test_console_safe_keeps_japanese_on_utf8_consoles(self):
        # The cp932 round trip is what produced the unreadable egg price keywords.
        self.assertEqual(fetch_rss.console_safe("卵価と価格の相場"), "卵価と価格の相場")


class CategoryTranslationRegressionTests(unittest.TestCase):
    """A fully translated food/egg headline keeps no ASCII token from the original,
    so the ai_dev subject-preservation rule must not be applied to it."""

    EGG_TRANSLATION = {
        "original_title": "Company launches plant-based egg product",
        "translated_title": "企業が植物由来の卵商品を発売",
        "translated_summary": [
            "食品メーカーが植物由来の卵代替商品を発売した",
            "大豆由来タンパクの加工技術を用いている",
            "国内の卵加工品の商品開発にも応用余地がある",
        ],
        "impact": "卵加工品の代替素材動向として確認する価値がある。",
    }

    def test_fully_translated_egg_title_is_accepted(self):
        self.assertTrue(
            fetch_rss.usable_newsroom_translation(self.EGG_TRANSLATION, "egg")
        )

    def test_ai_dev_still_requires_the_original_subject(self):
        self.assertFalse(
            fetch_rss.usable_newsroom_translation(self.EGG_TRANSLATION, "ai_dev")
        )

    def test_category_is_read_from_the_article_when_not_passed(self):
        item = dict(self.EGG_TRANSLATION, category="egg")
        self.assertTrue(fetch_rss.usable_newsroom_translation(item))

    def test_generic_egg_title_is_still_rejected(self):
        item = dict(self.EGG_TRANSLATION, translated_title="要確認: Something happened")
        self.assertFalse(fetch_rss.usable_newsroom_translation(item, "egg"))

    def test_english_egg_summary_is_still_rejected(self):
        item = dict(
            self.EGG_TRANSLATION,
            translated_summary=[
                "Company launches a plant based egg product line.",
                "It targets foodservice customers.",
                "The rollout starts in June.",
            ],
        )
        self.assertFalse(fetch_rss.usable_newsroom_translation(item, "egg"))


class SourceFeedbackHistoryRegressionTests(unittest.TestCase):
    @staticmethod
    def snapshot(run: int, likes: int, bads: int, displayed: int = 5, fallback: int = 0) -> dict:
        return {
            "generated_at": f"run-{run}",
            "categories": {
                "egg": {
                    "displayed": displayed,
                    "unique_sources": 1,
                    "sources": {
                        "Food Dive": {
                            "displayed": displayed,
                            "average_score": 60.0,
                            "fallback_count": fallback,
                            "likes": likes,
                            "bads": bads,
                            "net_feedback": likes - bads,
                        }
                    },
                }
            },
        }

    def test_repeated_runs_do_not_re_add_the_same_feedback(self):
        # Each snapshot stores the running total of the whole feedback file, so
        # summing across runs counted one like once per run.
        history = [self.snapshot(index, 3, 1) for index in range(30)]

        metrics = analyze_source_feedback.build_recommendations(history)["categories"]["egg"]["Food Dive"]

        self.assertEqual(metrics["runs_seen"], 30)
        self.assertEqual(metrics["likes"], 3)
        self.assertEqual(metrics["bads"], 1)
        self.assertEqual(metrics["net_feedback"], 2)

    def test_new_votes_on_the_newest_run_are_picked_up(self):
        history = [self.snapshot(index, 3, 1) for index in range(5)]
        history.append(self.snapshot(5, 5, 1))

        metrics = analyze_source_feedback.build_recommendations(history)["categories"]["egg"]["Food Dive"]

        self.assertEqual(metrics["likes"], 5)
        self.assertEqual(metrics["bads"], 1)

    def test_all_fallback_source_is_still_a_replace_candidate_over_many_runs(self):
        history = [self.snapshot(index, 0, 0, displayed=4, fallback=4) for index in range(12)]

        metrics = analyze_source_feedback.build_recommendations(history)["categories"]["egg"]["Food Dive"]

        self.assertEqual(metrics["average_fallback"], 4.0)
        self.assertEqual(metrics["average_displayed"], 4.0)
        self.assertEqual(metrics["recommendation"], "replace_candidate")

    def test_merge_history_keeps_earlier_runs(self):
        # The Actions cache restores this list; merging must extend it, not reset it.
        history = [self.snapshot(index, 1, 0) for index in range(3)]

        merged = analyze_source_feedback.merge_history(history, self.snapshot(3, 1, 0))

        self.assertEqual(len(merged), 4)
        self.assertEqual(
            [item["generated_at"] for item in merged],
            ["run-0", "run-1", "run-2", "run-3"],
        )


class TranslationKeyCoverageTests(unittest.TestCase):
    """Markup annotated with a key the dictionary lacks renders the key itself,
    which looks like working UI in a diff but shows "feedback_tools.copy" on the page."""

    ROOT = Path(__file__).resolve().parents[1]

    def markup_keys(self) -> set[str]:
        source = (self.ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
        keys = set(re.findall(r'data-i18n="([^"]+)"', source))
        for group in re.findall(r'data-i18n-attr="([^"]+)"', source):
            for pair in group.split(","):
                _, _, key = pair.partition(":")
                if key.strip():
                    keys.add(key.strip())
        return keys

    def dictionary_leaves(self) -> set[str]:
        source = (self.ROOT / "public" / "i18n.js").read_text(encoding="utf-8")
        return set(re.findall(r'^\s*(\w+):\s*"', source, flags=re.MULTILINE))

    def test_every_markup_key_exists_in_the_dictionary(self):
        keys = self.markup_keys()
        self.assertTrue(keys, "no data-i18n annotations found in the page template")
        leaves = self.dictionary_leaves()
        missing = sorted(key for key in keys if key.split(".")[-1] not in leaves)
        self.assertEqual(missing, [], f"data-i18n keys missing from public/i18n.js: {missing}")

    def test_app_js_holds_no_display_strings(self):
        source = (self.ROOT / "public" / "app.js").read_text(encoding="utf-8")
        japanese = re.findall(r"[぀-ヿ㐀-\u9fff]+", source)
        self.assertEqual(japanese, [], f"move this copy into public/i18n.js: {japanese}")



class ScriptEmbeddingRegressionTests(unittest.TestCase):
    """記事データを<script>へ埋め込む際のエスケープ。

    タイトルと要約は外部RSS由来で内容を制御できない。`</script>` を
    含む記事が1本でもあると、素の json.dumps ではscript要素がそこで
    終了し、以降がHTMLとして解釈される。
    """

    def test_closing_script_tag_cannot_break_out(self):
        payload = {
            "articles": [
                {"title": "速報 </script><img src=x onerror=alert(1)> 続報"}
            ]
        }
        embedded = build_site.embed_json(payload)
        self.assertNotIn("</script>", embedded)
        self.assertNotIn("<img", embedded)

    def test_escaped_json_still_parses_to_the_same_object(self):
        payload = {
            "articles": [
                {"title": "a < b </script>", "summary": ["<p>", "x"]},
            ],
            "categories": {"business": "ビジネス"},
        }
        self.assertEqual(json.loads(build_site.embed_json(payload)), payload)

    def test_japanese_text_is_not_escaped_to_ascii(self):
        embedded = build_site.embed_json({"title": "卵価格の動向"})
        self.assertIn("卵価格の動向", embedded)

class ConfigLocationTests(unittest.TestCase):
    """The engine must run against a theme pack outside this repository, and must
    behave exactly as before when the environment says nothing."""

    ENV_VARS = ("NEWSROOM_CONFIG_DIR", "NEWSROOM_STATE_DIR")

    def setUp(self):
        self.saved = {name: os.environ.get(name) for name in self.ENV_VARS}
        for name in self.ENV_VARS:
            os.environ.pop(name, None)

    def tearDown(self):
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_defaults_are_the_in_repository_layout(self):
        self.assertEqual(newsroom_config.config_dir(), newsroom_config.ROOT / "config")
        self.assertEqual(newsroom_config.state_dir(), newsroom_config.ROOT / "data")
        self.assertEqual(
            newsroom_config.config_path("sources.yaml"),
            newsroom_config.ROOT / "config" / "sources.yaml",
        )
        self.assertEqual(
            newsroom_config.state_path("feedback.json"),
            newsroom_config.ROOT / "data" / "feedback.json",
        )

    def test_environment_overrides_both_directories(self):
        os.environ["NEWSROOM_CONFIG_DIR"] = "/themes/personal"
        os.environ["NEWSROOM_STATE_DIR"] = "/themes/personal/state"

        self.assertEqual(
            newsroom_config.config_path("preferences.yaml"),
            Path("/themes/personal/preferences.yaml"),
        )
        self.assertEqual(
            newsroom_config.state_path("run_history.json"),
            Path("/themes/personal/state/run_history.json"),
        )

    def test_blank_environment_value_falls_back_to_the_default(self):
        os.environ["NEWSROOM_CONFIG_DIR"] = "   "
        self.assertEqual(newsroom_config.config_dir(), newsroom_config.ROOT / "config")

    def test_every_pipeline_script_reads_through_the_config_layer(self):
        # A script that hardcodes ROOT / "data" would silently ignore a theme pack.
        scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
        offenders = []
        for path in sorted(scripts_dir.glob("*.py")):
            if path.name == "newsroom_config.py":
                continue
            source = path.read_text(encoding="utf-8")
            # Match the prefix, not the exact string: ROOT / "config/preferences.yaml"
            # slipped past the closed-quote form and read the public config even
            # when a theme pack was configured.
            if 'ROOT / "data' in source or 'ROOT / "config' in source:
                offenders.append(path.name)
        self.assertEqual(offenders, [])


class FeedUrlInjectionTests(unittest.TestCase):
    """Feed URLs that must not be committed are referenced by name and injected."""

    LOOKUP = "GOOGLE_ALERT_TEST_FEED"
    ENV_VARS = (LOOKUP, newsroom_config.FEED_BUNDLE_ENV)
    ALERT = "https://example.com/alerts/feeds/direct"
    BUNDLED = "https://example.com/alerts/feeds/bundled"
    LITERAL = "https://example.com/alerts/feeds/literal"

    def setUp(self):
        self.saved = {name: os.environ.get(name) for name in self.ENV_VARS}
        for name in self.ENV_VARS:
            os.environ.pop(name, None)

    def tearDown(self):
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def source(self, **overrides) -> dict:
        item = {"name": "Google Alert: test", "source_type": "google_alert", "url_env": self.LOOKUP}
        item.update(overrides)
        return item

    def test_dedicated_environment_variable_is_used(self):
        os.environ[self.LOOKUP] = self.ALERT
        self.assertEqual(newsroom_config.resolve_source_url(self.source()), self.ALERT)

    def test_bundle_supplies_the_url_when_no_dedicated_variable_exists(self):
        os.environ[newsroom_config.FEED_BUNDLE_ENV] = json.dumps({self.LOOKUP: self.BUNDLED})
        self.assertEqual(newsroom_config.resolve_source_url(self.source()), self.BUNDLED)

    def test_dedicated_variable_wins_over_the_bundle(self):
        os.environ[self.LOOKUP] = self.ALERT
        os.environ[newsroom_config.FEED_BUNDLE_ENV] = json.dumps({self.LOOKUP: self.BUNDLED})
        self.assertEqual(newsroom_config.resolve_source_url(self.source()), self.ALERT)

    def test_literal_url_still_works_when_nothing_is_injected(self):
        # Keeps a checkout that carries its own URLs behaving as before.
        self.assertEqual(
            newsroom_config.resolve_source_url(self.source(url=self.LITERAL)),
            self.LITERAL,
        )

    def test_injected_url_overrides_the_literal_one(self):
        os.environ[self.LOOKUP] = self.ALERT
        self.assertEqual(
            newsroom_config.resolve_source_url(self.source(url=self.LITERAL)),
            self.ALERT,
        )

    def test_unresolvable_source_yields_no_url(self):
        self.assertEqual(newsroom_config.resolve_source_url(self.source()), "")

    def test_malformed_bundle_is_ignored_rather_than_raising(self):
        os.environ[newsroom_config.FEED_BUNDLE_ENV] = "{not json"
        self.assertEqual(newsroom_config.feed_bundle(), {})
        self.assertEqual(
            newsroom_config.resolve_source_url(self.source(url=self.LITERAL)),
            self.LITERAL,
        )

    def test_normalize_source_injects_the_url_for_collectors(self):
        # collectors/rss.py reads source["url"], so resolution happens before it.
        os.environ[self.LOOKUP] = self.ALERT
        normalized = fetch_rss.normalize_source(self.source())
        self.assertEqual(normalized["url"], self.ALERT)
        self.assertEqual(normalized["source_type"], "google_alert")

    def test_unresolved_source_is_skipped_and_the_run_continues(self):
        with self.assertRaises(ValueError) as caught:
            fetch_rss.fetch_source(self.source(), "food", "スイーツ・飲食")
        self.assertIn(self.LOOKUP, str(caught.exception))

    def test_failure_message_names_the_lookup_but_never_a_url(self):
        os.environ[newsroom_config.FEED_BUNDLE_ENV] = json.dumps({"OTHER": self.BUNDLED})
        message = newsroom_config.describe_unresolved_source(self.source())
        self.assertIn(self.LOOKUP, message)
        self.assertNotIn(self.BUNDLED, message)
        self.assertNotIn("https://", message)


class SourcesConfigTests(unittest.TestCase):
    def test_every_google_alert_names_an_injection_lookup(self):
        # Production alert endpoints are supplied only through Actions secrets.
        import yaml

        config = yaml.safe_load(
            (Path(__file__).resolve().parents[1] / "config" / "sources.yaml").read_text(encoding="utf-8")
        )
        alerts = [
            source
            for category in config["categories"].values()
            for source in category.get("sources", [])
            if source.get("source_type") == "google_alert"
        ]
        self.assertTrue(alerts)
        missing = [source["name"] for source in alerts if not source.get("url_env")]
        self.assertEqual(missing, [])
        self.assertTrue(all("url" not in source for source in alerts))


class InjectedUrlRedactionTests(unittest.TestCase):
    """An injected feed URL must not reach the log.

    requests reports a failure as "...(host='www.google.com')... with url: /alerts/
    feeds/<id>/<token>", splitting host from path. GitHub only masks an exact
    match of the registered secret, so the path would otherwise survive into a
    public Actions log and defeat the point of injecting the URL at all.
    """

    LOOKUP = "GOOGLE_ALERT_REDACTION_TEST"
    SECRET_URL = "https://www.google.com/alerts/feeds/11112222333344445555/6666777788889999"
    SECRET_PATH = "/alerts/feeds/11112222333344445555/6666777788889999"

    def setUp(self):
        newsroom_logging.reset_secrets()
        self.saved = os.environ.get(self.LOOKUP)
        os.environ[self.LOOKUP] = self.SECRET_URL
        self.logger = newsroom_logging.get_logger()
        self.records: list[str] = []

        formatter = newsroom_logging._RedactingFormatter("%(message)s")

        class Collector(logging.Handler):
            def emit(inner, record):
                self.records.append(formatter.format(record))

        self.handler = Collector(level=logging.DEBUG)
        self.logger.addHandler(self.handler)
        self.previous_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.previous_level)
        if self.saved is None:
            os.environ.pop(self.LOOKUP, None)
        else:
            os.environ[self.LOOKUP] = self.saved
        newsroom_logging.reset_secrets()

    def resolve(self) -> str:
        return newsroom_config.resolve_source_url(
            {"name": "Google Alert: test", "source_type": "google_alert", "url_env": self.LOOKUP}
        )

    def test_resolution_returns_the_real_url_to_the_caller(self):
        # Redaction is a logging concern; the collector still needs the real URL.
        self.assertEqual(self.resolve(), self.SECRET_URL)

    def test_full_url_is_scrubbed_from_the_log(self):
        self.resolve()
        self.logger.warning(f"[rss_failure] fetch failed for {self.SECRET_URL}")
        self.assertNotIn(self.SECRET_URL, self.records[-1])
        self.assertIn(newsroom_logging.REDACTED, self.records[-1])

    def test_path_alone_is_scrubbed_from_the_log(self):
        self.resolve()
        self.logger.warning(
            "HTTPSConnectionPool(host='www.google.com', port=443): "
            f"Max retries exceeded with url: {self.SECRET_PATH} (Caused by ProxyError)"
        )
        message = self.records[-1]
        self.assertNotIn(self.SECRET_PATH, message)
        self.assertIn(newsroom_logging.REDACTED, message)
        # The surrounding diagnostic detail is still readable.
        self.assertIn("ProxyError", message)

    def test_traceback_text_is_scrubbed(self):
        self.resolve()
        try:
            raise RuntimeError(f"connection to {self.SECRET_URL} failed")
        except RuntimeError:
            self.logger.debug("[source] fetch failed", exc_info=True)
        self.assertNotIn(self.SECRET_URL, self.records[-1])

    def test_a_literal_url_from_the_config_file_is_not_redacted(self):
        # Only injected values are secret; a URL committed in sources.yaml is not.
        literal = "https://www3.nhk.or.jp/rss/news/cat5.xml"
        newsroom_config.resolve_source_url({"name": "NHK", "source_type": "rss", "url": literal})
        self.logger.info(f"[rss_summary] {literal}")
        self.assertIn(literal, self.records[-1])

    def test_short_values_are_not_registered(self):
        # Guards against a stray short value blanking out ordinary log text.
        newsroom_logging.register_secret("ok")
        self.logger.info("everything is ok here")
        self.assertIn("ok here", self.records[-1])


class ExampleThemePackTests(unittest.TestCase):
    """themes/example/ is the entry point for anyone who clones this repository,
    and it is public. It has to keep working, and it must never carry a feed URL
    that belongs in a private pack."""

    ROOT = Path(__file__).resolve().parents[1]
    PACK = ROOT / "themes" / "example"

    def load(self, filename: str) -> dict:
        import yaml

        return yaml.safe_load((self.PACK / filename).read_text(encoding="utf-8"))

    def sources(self) -> list[dict]:
        config = self.load("sources.yaml")
        return [
            source
            for category in config["categories"].values()
            for source in category.get("sources", [])
        ]

    def test_pack_carries_the_three_theme_files(self):
        for filename in ("sources.yaml", "preferences.yaml", "prompts.yaml"):
            self.assertTrue((self.PACK / filename).is_file(), filename)

    def test_no_google_alert_feed_reaches_the_public_pack(self):
        # A personal alert URL cannot be rotated, so it must never land here.
        for source in self.sources():
            self.assertNotEqual(source.get("source_type"), "google_alert", source.get("name"))
        for path in sorted(self.PACK.rglob("*")):
            if path.is_file():
                self.assertNotIn("alerts/feeds", path.read_text(encoding="utf-8"), str(path))

    def test_every_sample_source_is_directly_fetchable(self):
        # The sample must work on a bare clone, so no source may need a secret.
        for source in self.sources():
            self.assertNotIn("url_env", source, source.get("name"))
            url = str(source.get("url") or "")
            self.assertTrue(url.startswith("https://"), source.get("name"))
            self.assertEqual(url, url.strip(), source.get("name"))
            self.assertNotIn("\n", url, source.get("name"))

    def test_pack_covers_the_category_keys_the_engine_requires(self):
        # The keys are still hardcoded across the pipeline and the page.
        required = set(validate_newsroom.CATEGORY_ORDER)
        self.assertEqual(set(self.load("sources.yaml")["categories"]), required)
        self.assertEqual(set(self.load("preferences.yaml")["categories"]), required)

    def test_every_category_names_a_label_and_at_least_one_source(self):
        for key, category in self.load("sources.yaml")["categories"].items():
            self.assertTrue(str(category.get("label") or "").strip(), key)
            self.assertTrue(category.get("sources"), key)

    def test_preferences_carry_every_weight_the_scorer_reads(self):
        scoring = self.load("preferences.yaml")["scoring"]
        for weight in ("keyword_weight", "recency_weight", "source_weight", "feedback_weight"):
            self.assertIn(weight, scoring)

    def test_the_scorer_runs_against_the_sample_pack(self):
        prefs = self.load("preferences.yaml")
        item = article("sample", "ai_dev", title="生成AIの活用事例とLLMのAPI更新")
        score = score_articles.score_article(item, prefs, {})
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)


class ReaderThemeIntegrationTests(unittest.TestCase):
    def test_reader_vocabulary_uses_external_theme(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.yaml").write_text(
                "categories:\n  food:\n    boost_keywords: [external-topic]\n    learned_tags: {learned-topic: 2}\n",
                encoding="utf-8",
            )
            index = root / "index.html"
            with patch.dict(os.environ, {"NEWSROOM_CONFIG_DIR": str(root), "NEWSROOM_STATE_DIR": str(root)}), \
                 patch.object(build_site, "load_articles", return_value=[]), \
                 patch.object(build_site, "PUBLIC_DIR", root), \
                 patch.object(build_site, "INDEX_PATH", index):
                build_site.main()
            payload = json.loads(re.search(
                r'<script id="newsData" type="application/json">(.*?)</script>',
                index.read_text(encoding="utf-8"), re.S,
            ).group(1))
            self.assertEqual(payload["vocabulary"], {"food": ["external-topic", "learned-topic"]})


if __name__ == "__main__":
    unittest.main()
