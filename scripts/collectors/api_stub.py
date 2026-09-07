from __future__ import annotations

from typing import Any

from newsroom_logging import get_logger


LOG = get_logger()


def collect_api_stub(source: dict[str, Any]) -> list[dict[str, Any]]:
    LOG.debug(f"[api_stub] {source['name']}: collector not implemented yet")
    return []
