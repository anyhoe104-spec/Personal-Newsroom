import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_rss


class FreshnessTests(unittest.TestCase):
    def test_dates_preserve_publication_and_unknown(self):
        self.assertEqual(fetch_rss.parse_date({'published': '2026-09-18T12:00:00+09:00'}), '2026-09-18T03:00:00+00:00')
        self.assertEqual(fetch_rss.parse_date({'published': 'Fri, 18 Sep 2026 03:00:00 GMT'}), '2026-09-18T03:00:00+00:00')
        for entry in [{}, {'published': 'broken'}, {'published': 'broken', 'updated': '2026-09-19T00:00:00Z'}]:
            self.assertEqual(fetch_rss.parse_date(entry), '')

    def test_cutoff_unknown_future_and_old_updated_article(self):
        now = datetime(2026, 9, 19, tzinfo=timezone.utc)
        for age, expected in [(timedelta(days=7), True), (timedelta(days=7, seconds=1), False), (timedelta(days=-2), False)]:
            self.assertEqual(fetch_rss.recent_entry({'published': (now-age).isoformat()}, now), expected)
        self.assertFalse(fetch_rss.recent_entry({}, now))
        self.assertFalse(fetch_rss.recent_entry({'published': '2026-08-07T01:30:00Z', 'updated': now.isoformat()}, now))

    def test_active_collector_excludes_stale_before_normalization(self):
        now = datetime.now(timezone.utc)
        entries = [{'title': str(i), 'published': (now-timedelta(days=age)).isoformat()} for i, age in enumerate([0, 2, 43])]
        entries.append({'title': 'unknown'})
        with patch.dict(fetch_rss.COLLECTORS, {'rss': lambda _: entries}), patch.object(fetch_rss, 'normalize_entry', side_effect=lambda entry, *_: entry) as normalize:
            result = fetch_rss.fetch_source({'name': 'QA', 'url': 'https://example.org/rss'}, 'business', 'Business')
        self.assertEqual([e['title'] for e in result], ['0', '1'])
        self.assertEqual(normalize.call_count, 2)

    def test_feed_with_nothing_recent_is_reported_as_stale(self):
        # NHK cat5.xml kept answering with the same 2026-08-07 items for weeks.
        frozen = [{'title': str(i), 'published': f'2026-08-0{i + 5}T01:30:00Z'} for i in range(3)]
        frozen.append({'title': 'undated'})
        stale_before = len(fetch_rss.RUN_STATS['stale_sources'])
        with patch.dict(fetch_rss.COLLECTORS, {'rss': lambda _: frozen}):
            self.assertEqual(fetch_rss.fetch_source({'name': 'Frozen', 'url': 'https://example.org/rss'}, 'business', 'Business'), [])
        reported = fetch_rss.RUN_STATS['stale_sources'][stale_before:]
        self.assertEqual(reported, [{'category': 'business', 'source': 'Frozen', 'entries': 4, 'newest': '2026-08-07'}])

    def test_quiet_or_recent_feeds_are_not_stale(self):
        now = datetime.now(timezone.utc)
        stale_before = len(fetch_rss.RUN_STATS['stale_sources'])
        for entries in ([], [{'title': 'new', 'published': now.isoformat()}]):
            with patch.dict(fetch_rss.COLLECTORS, {'rss': lambda _, e=entries: e}), patch.object(fetch_rss, 'normalize_entry', side_effect=lambda entry, *_: entry):
                fetch_rss.fetch_source({'name': 'QA', 'url': 'https://example.org/rss'}, 'business', 'Business')
        self.assertEqual(len(fetch_rss.RUN_STATS['stale_sources']), stale_before)
