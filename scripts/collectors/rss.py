from __future__ import annotations

from typing import Any

import feedparser
import requests
from newsroom_logging import get_logger


LOG = get_logger()
USER_AGENT = "Personal-Newsroom/1.0 (+https://github.com/anyhoe104-spec/Personal-Newsroom)"


def collect_rss(source: dict[str, Any]) -> list[dict[str, Any]]:
    response = requests.get(
        source["url"],
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if getattr(feed, "bozo", False):
        reason = getattr(feed, "bozo_exception", "unknown parse error")
        # feedparser flags many well-formed feeds as bozo, so this is diagnostic only.
        LOG.debug(f"[rss] {source['name']}: parse warning: {reason}")
    return list(feed.entries[: source.get("limit", 30)])
