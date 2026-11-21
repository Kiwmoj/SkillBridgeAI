"""Load the official O*NET release automatically when a hosted database has none.

Runs once in a background thread so startup and health checks are not blocked. It is opt-in
(``ONET_AUTO_IMPORT``) and does nothing when an O*NET release is already active.
"""
import logging
import tempfile
import threading
import urllib.request
from pathlib import Path

from apps.backend.core import config
from apps.backend.database.session import SessionLocal
from apps.backend.repositories import training as training_repository
from apps.backend.services.careers.onet_import import OnetImportError, import_onet_zip, register_import

logger = logging.getLogger(__name__)
_started = threading.Lock()
DOWNLOAD_TIMEOUT_SECONDS = 120


def needs_import() -> bool:
    with SessionLocal() as db:
        return training_repository.latest_imported_dataset(db) is None


def run_import() -> dict | None:
    settings = config.settings
    if not needs_import():
        logger.info("O*NET auto-import skipped: a release is already loaded.")
        return None
    logger.info("O*NET auto-import: downloading %s", settings.onet_archive_url)
    with tempfile.TemporaryDirectory(prefix="onet-") as directory:
        archive = Path(directory) / "onet.zip"
        with urllib.request.urlopen(settings.onet_archive_url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            archive.write_bytes(response.read())
        with SessionLocal() as db:
            try:
                result = import_onet_zip(db, str(archive), "user-supplied", settings.onet_skip_files)
                register_import(db, result)
                db.commit()
            except Exception:
                db.rollback()
                raise
    logger.info("O*NET auto-import complete: %s occupations, %s descriptors (version %s).",
                result["occupations"], result["descriptors"], result["version"])
    return result


def _worker() -> None:
    try:
        run_import()
    except (OSError, OnetImportError) as exc:
        logger.error("O*NET auto-import failed: %s", exc)
    except Exception:
        logger.exception("O*NET auto-import failed unexpectedly.")


def start_background_import() -> bool:
    """Start the one-time import thread if enabled; return True when a thread was started."""
    if not config.settings.onet_auto_import or not _started.acquire(blocking=False):
        return False
    threading.Thread(target=_worker, name="onet-auto-import", daemon=True).start()
    return True
