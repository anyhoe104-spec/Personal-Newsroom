"""Shared logging setup for the Personal-Newsroom pipeline scripts.

Console output keeps the existing ``[tag] message`` shape so the Actions log
reading guide in README stays valid. Levels decide what actually reaches the
console: production runs stay at INFO, and the per-article diagnostics that used
to dominate a run are DEBUG.

Environment variables:

- ``NEWSROOM_LOG_LEVEL`` (or ``LOG_LEVEL``): console level, default ``INFO``.
- ``NEWSROOM_LOG_FILE``: log file path, default ``logs/newsroom.log``.
  Set to an empty value to disable file logging.
- ``NEWSROOM_LOG_FILE_LEVEL``: file level, default ``DEBUG``.
- ``NEWSROOM_LOG_MAX_BYTES``: rotation size per file, default 1 MiB.
- ``NEWSROOM_LOG_BACKUP_COUNT``: rotated files kept, default 3.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGGER_NAME = "newsroom"
DEFAULT_CONSOLE_LEVEL = "INFO"
DEFAULT_FILE_LEVEL = "DEBUG"
DEFAULT_LOG_FILE = ROOT / "logs" / "newsroom.log"
DEFAULT_MAX_BYTES = 1024 * 1024
DEFAULT_BACKUP_COUNT = 3

_configured = False
_capped_counts: dict[str, int] = {}
_capped_limits: dict[str, int] = {}


def _env_level(name: str, default: str) -> int:
    raw = (os.getenv(name) or "").strip().upper()
    if not raw:
        return logging.getLevelName(default)
    level = logging.getLevelName(raw)
    return level if isinstance(level, int) else logging.getLevelName(default)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def console_level() -> int:
    raw = (os.getenv("NEWSROOM_LOG_LEVEL") or "").strip()
    if raw:
        return _env_level("NEWSROOM_LOG_LEVEL", DEFAULT_CONSOLE_LEVEL)
    return _env_level("LOG_LEVEL", DEFAULT_CONSOLE_LEVEL)


def log_file_path() -> Path | None:
    raw = os.getenv("NEWSROOM_LOG_FILE")
    if raw is None:
        return DEFAULT_LOG_FILE
    raw = raw.strip()
    return Path(raw) if raw else None


def configure_logging() -> logging.Logger:
    """Install console and rotating-file handlers once per process."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    logger.propagate = False
    logger.handlers.clear()

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(console_level())
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    file_level = _env_level("NEWSROOM_LOG_FILE_LEVEL", DEFAULT_FILE_LEVEL)
    path = log_file_path()
    if path is not None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                path,
                maxBytes=_env_int("NEWSROOM_LOG_MAX_BYTES", DEFAULT_MAX_BYTES),
                backupCount=_env_int("NEWSROOM_LOG_BACKUP_COUNT", DEFAULT_BACKUP_COUNT),
                encoding="utf-8",
            )
        except OSError as exc:
            # A read-only or missing directory must never stop a pipeline run.
            console.handle(
                logger.makeRecord(
                    LOGGER_NAME, logging.WARNING, __file__, 0,
                    f"[logging] file logging disabled: {exc}", (), None,
                )
            )
        else:
            file_handler.setLevel(file_level)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            )
            logger.addHandler(file_handler)
    else:
        file_level = logging.CRITICAL

    logger.setLevel(min(console.level, file_level))
    _configured = True
    return logger


def get_logger() -> logging.Logger:
    return configure_logging()


def set_capped_limit(group: str, limit: int) -> None:
    """Cap how many records ``group`` may emit during this run."""
    _capped_limits[group] = limit


def log_capped(level: int, group: str, message: str, limit: int | None = None) -> None:
    """Log ``message`` unless ``group`` already hit its per-run limit.

    Repetitive per-article diagnostics use this so a bad run cannot flood the
    log with one line per article.
    """
    logger = get_logger()
    if limit is not None:
        _capped_limits.setdefault(group, limit)
    effective_limit = _capped_limits.get(group, 10)
    seen = _capped_counts.get(group, 0)
    _capped_counts[group] = seen + 1
    if seen < effective_limit:
        logger.log(level, message)
    elif seen == effective_limit:
        logger.log(
            level,
            f"[log_capped] {group}: reached {effective_limit} messages; suppressing the rest",
        )


def log_suppression_summary() -> None:
    """Report groups that were truncated, so the cap is never silent."""
    logger = get_logger()
    for group, count in sorted(_capped_counts.items()):
        limit = _capped_limits.get(group, 10)
        if count > limit:
            logger.info(f"[log_capped] {group}: emitted={limit}, suppressed={count - limit}")


def reset_caps() -> None:
    _capped_counts.clear()
    _capped_limits.clear()
