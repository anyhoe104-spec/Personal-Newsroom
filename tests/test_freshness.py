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
