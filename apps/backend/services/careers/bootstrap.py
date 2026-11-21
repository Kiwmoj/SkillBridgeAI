"""Load the official O*NET release automatically when a hosted database is missing it.

Runs once in a background thread so startup and health checks are not blocked. It is opt-in
(``ONET_AUTO_IMPORT``). A full import runs when no release is active; databases imported before the
reference tables existed only receive the small definitions/education/job-zone tables.
"""
import logging
import tempfile
import threading
import urllib.request
from pathlib import Path

from apps.backend.core import config
from apps.backend.database.session import SessionLocal
from apps.backend.models import OnetElement
from apps.backend.repositories import training as training_repository
from apps.backend.services.careers.onet_import import (
    OnetImportError,
    import_onet_references,
    import_onet_zip,
    register_import,
)

logger = logging.getLogger(__name__)
_started = threading.Lock()
DOWNLOAD_TIMEOUT_SECONDS = 120


def needs_import() -> bool:
    with SessionLocal() as db:
        return training_repository.latest_imported_dataset(db) is None


def needs_references() -> bool:
    with SessionLocal() as db:
        return db.query(OnetElement).first() is None


def _download(url: str, target: Path) -> None:
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        target.write_bytes(response.read())


def run_import() -> dict | None:
    settings = config.settings
    full, references = needs_import(), needs_references()
    if not full and not references:
        logger.info("O*NET auto-import skipped: release and reference data already loaded.")
        return None
    logger.info("O*NET auto-import (%s): downloading %s", "full" if full else "references", settings.onet_archive_url)
    with tempfile.TemporaryDirectory(prefix="onet-") as directory:
        archive = Path(directory) / "onet.zip"
        _download(settings.onet_archive_url, archive)
        with SessionLocal() as db:
            try:
                if full:
                    result = import_onet_zip(db, str(archive), "user-supplied", settings.onet_skip_files)
                    register_import(db, result)
                else:
                    result = {"reference_rows": import_onet_references(db, str(archive))}
                db.commit()
            except Exception:
                db.rollback()
                raise
    logger.info("O*NET auto-import complete: %s", {k: v for k, v in result.items() if k != "files"})
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
