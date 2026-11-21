"""Logging setup shared by the API, CLIs, and migrations.

Log lines never include passwords, tokens, API keys, database credentials, or request bodies;
callers log event types and identifiers only.
"""
import logging


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    if root.handlers:
        # Another component (such as Alembic's fileConfig) already installed handlers; keep them.
        root.setLevel(level)
    else:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
