from __future__ import annotations

from typing import Any

from .rss import collect_rss


def collect_google_alert(source: dict[str, Any]) -> list[dict[str, Any]]:
    return collect_rss(source)
