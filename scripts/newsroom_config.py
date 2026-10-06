"""The boundary between the engine and its configuration.

The pipeline in ``scripts/`` is generic; what makes it *this* newsroom lives in
``config/`` and ``data/``. This module is the only place that decides where
those live, so the engine can run against a theme pack stored outside this
repository.

Environment variables:

- ``NEWSROOM_CONFIG_DIR``: holds ``sources.yaml``, ``preferences.yaml`` and
  ``prompts.yaml``. Default ``config/``.
- ``NEWSROOM_STATE_DIR``: holds ``articles.json``, ``feedback.json``,
  ``run_history.json`` and ``source_recommendations.json``. Default ``data/``.
- ``GOOGLE_ALERT_FEEDS``: JSON object mapping a lookup name to a feed URL, for
  injecting several feed URLs through one secret.

Every default reproduces the in-repository layout, so an unset environment
behaves exactly as before.

Feed URLs that should not be committed are referenced by name from
``sources.yaml`` instead of being written out:

    - name: "Google Alert: スイーツ 新商品"
      source_type: "google_alert"
      url_env: "GOOGLE_ALERT_SWEETS"

``url_env`` names a lookup that is resolved from the environment variable of
that name, or from the ``GOOGLE_ALERT_FEEDS`` bundle. A literal ``url`` is used
when the lookup finds nothing, which keeps a checkout that carries its own URLs
working unchanged.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from urllib.parse import urlsplit

from newsroom_logging import get_logger, register_secret


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = ROOT / "config"
DEFAULT_STATE_DIR = ROOT / "data"
FEED_BUNDLE_ENV = "GOOGLE_ALERT_FEEDS"

LOG = get_logger()


def _dir_from_env(name: str, default: Path) -> Path:
    raw = (os.getenv(name) or "").strip()
    return Path(raw).expanduser() if raw else default


def config_dir() -> Path:
    """Directory holding the YAML configuration files."""
    return _dir_from_env("NEWSROOM_CONFIG_DIR", DEFAULT_CONFIG_DIR)


def state_dir() -> Path:
    """Directory holding article data and accumulated learning state."""
    return _dir_from_env("NEWSROOM_STATE_DIR", DEFAULT_STATE_DIR)


def config_path(filename: str) -> Path:
    return config_dir() / filename


def state_path(filename: str) -> Path:
    return state_dir() / filename


def feed_bundle() -> dict[str, str]:
    """Parse ``GOOGLE_ALERT_FEEDS`` into a name-to-URL mapping.

    A malformed bundle is reported and ignored rather than failing the run: one
    unusable secret must not stop the other sources from being fetched. The
    value is never logged.
    """
    raw = (os.getenv(FEED_BUNDLE_ENV) or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        LOG.warning(f"[source_config] {FEED_BUNDLE_ENV} is not valid JSON: {exc}")
        return {}
    if not isinstance(parsed, dict):
        LOG.warning(f"[source_config] {FEED_BUNDLE_ENV} must be a JSON object of name to URL")
        return {}
    return {str(key): str(value) for key, value in parsed.items() if str(value).strip()}


def _keep_out_of_logs(url: str) -> str:
    """Register an injected URL for redaction, then return it unchanged.

    Both the whole URL and its path are registered: a failed request reports the
    host and the path separately, so scrubbing the full string alone would leave
    the identifying part in the log.
    """
    register_secret(url)
    path = urlsplit(url).path
    if path and path != "/":
        register_secret(path)
    return url


def resolve_source_url(source: dict) -> str:
    """Return the feed URL for ``source``, resolving ``url_env`` when present.

    Precedence is the dedicated environment variable, then the
    ``GOOGLE_ALERT_FEEDS`` bundle, then a literal ``url``. Returns an empty
    string when nothing resolves; the caller reports and skips the source.
    Neither the URL nor the environment value is logged.
    """
    lookup = str(source.get("url_env") or "").strip()
    if lookup:
        direct = (os.getenv(lookup) or "").strip()
        if direct:
            return _keep_out_of_logs(direct)
        bundled = feed_bundle().get(lookup, "").strip()
        if bundled:
            return _keep_out_of_logs(bundled)
    return str(source.get("url") or "").strip()


def source_with_resolved_url(source: dict) -> dict:
    """Copy of ``source`` with ``url`` filled in from the environment."""
    resolved = dict(source)
    url = resolve_source_url(source)
    if url:
        resolved["url"] = url
    return resolved


def describe_unresolved_source(source: dict) -> str:
    """Explain why a source has no URL, naming only the lookup, never a value."""
    lookup = str(source.get("url_env") or "").strip()
    if lookup:
        return (
            f"url_env={lookup} is not set in the environment or in {FEED_BUNDLE_ENV}, "
            "and no literal url is configured"
        )
    return "no url or url_env is configured"


def log_config_locations(level: int = logging.INFO) -> None:
    """Record which configuration and state directories this run used."""
    LOG.log(level, f"[source_config] config_dir={config_dir()}, state_dir={state_dir()}")
