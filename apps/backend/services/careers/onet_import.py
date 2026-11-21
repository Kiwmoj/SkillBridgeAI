"""Store an official O*NET archive in the application database.

Parsing lives in ``packages.onet``; this module owns the SQLAlchemy writes and the dataset
bookkeeping that make a release the active reference data.
"""
import csv
import json
import zipfile
from collections import Counter
from typing import BinaryIO

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from apps.backend.models import (
    AlternateTitle, DatasetVersion, Descriptor, Occupation, RelatedOccupation, TrainingHistory,
)
from packages.onet.constants import ONET_URL
from packages.onet.parser import (
    ArchiveMember,
    OnetArchive,
    OnetParseError,
    alternate_title,
    descriptor_element_id,
    descriptor_name,
    descriptor_rating,
    related_code,
    row_code,
)

BATCH_SIZE = 2000


class OnetImportError(RuntimeError):
    pass


def import_onet_zip(db: Session, path: str | BinaryIO, version: str, skip_files: frozenset[str] = frozenset()) -> dict:
    """Replace the imported reference rows for this release, preserving occupation IDs."""
    try:
        with zipfile.ZipFile(path) as archive:
            return _import_archive(db, OnetArchive(archive), version, skip_files)
    except OnetParseError as exc:
        raise OnetImportError(str(exc)) from exc
    except (zipfile.BadZipFile, UnicodeError, csv.Error, NotImplementedError, RuntimeError) as exc:
        if isinstance(exc, OnetImportError):
            raise
        raise OnetImportError("Unreadable O*NET ZIP. Use the official UTF-8 CSV or text ZIP.") from exc


def register_import(db: Session, result: dict) -> None:
    """Mark the imported release as the active dataset and record it in the audit history."""
    name = f"O*NET {result['version']}"
    dataset = db.query(DatasetVersion).filter_by(name=name).first()
    if not dataset:
        dataset = DatasetVersion(name=name, status="imported")
        db.add(dataset)
    # Only the most recent import is active; retain audit data for earlier releases.
    db.execute(update(DatasetVersion).where(
        DatasetVersion.status == "imported", DatasetVersion.name != name,
    ).values(status="archived"))
    dataset.status = "imported"
    db.flush()
    db.add(TrainingHistory(dataset_version_id=dataset.id, action="onet_import",
                           status="completed", details=json.dumps(result)))


def _add_batch(db: Session, table, batch: list[dict]) -> None:
    if batch:
        db.execute(insert(table), batch)
        batch.clear()


def _import_archive(db: Session, archive: OnetArchive, version: str, skip_files: frozenset[str] = frozenset()) -> dict:
    version = archive.resolve_version(version)
    saved = {item.onet_soc_code: item for item in db.scalars(select(Occupation))}
    loaded: dict[str, Occupation] = {}
    for row in archive.occupations():
        occupation = saved.get(row.code)
        if occupation is None:
            occupation = Occupation(onet_soc_code=row.code)
            db.add(occupation)
        occupation.title = row.title
        occupation.description = row.description
        occupation.dataset_version = version
        loaded[row.code] = occupation
    db.flush()
    ids = {code: item.id for code, item in loaded.items()}

    # Remove old reference details for updated codes without deleting saved careers.
    occupation_ids = select(Occupation.id).where(Occupation.dataset_version == version)
    for table in (AlternateTitle, Descriptor, RelatedOccupation):
        db.execute(delete(table).where(table.occupation_id.in_(occupation_ids)))
    for code, occupation in saved.items():
        if code not in loaded:
            occupation.dataset_version = None

    counts = Counter(occupations=len(ids), alternate_titles=0, descriptors=0, related_occupations=0, skipped_rows=0)
    file_counts: Counter[str] = Counter()
    aliases: set[tuple[int, str]] = set()
    related: set[tuple[int, str]] = set()
    for member in archive.members:
        kind = member.kind
        if kind is None or member.key in skip_files:
            continue
        table = AlternateTitle if kind == "titles" else RelatedOccupation if kind == "related" else Descriptor
        batch: list[dict] = []
        seen_descriptors: set[tuple] = set()
        file_counts[member.filename] = 0
        for row in archive.rows(member):
            occupation_id = ids.get(row_code(row))
            if occupation_id is None:
                counts["skipped_rows"] += 1
                continue
            record = _record(kind, member, row, occupation_id, aliases, related, seen_descriptors)
            if record is None:
                counts["skipped_rows"] += 1
                continue
            if record:
                batch.append(record)
                file_counts[member.filename] += 1
                counts["alternate_titles" if kind == "titles" else
                       "related_occupations" if kind == "related" else "descriptors"] += 1
            if len(batch) == BATCH_SIZE:
                _add_batch(db, table, batch)
        _add_batch(db, table, batch)
    return {**counts, "version": version, "files": dict(file_counts), "source": ONET_URL}


def _record(kind: str, member: ArchiveMember, row: dict[str, str], occupation_id: int,
            aliases: set, related: set, seen_descriptors: set) -> dict | None:
    """Build an insert row; return None for an invalid row and {} for a duplicate that is silently dropped."""
    if kind == "titles":
        title = alternate_title(row)
        if title is None:
            return None
        key = (occupation_id, title.casefold())
        if key in aliases:
            return {}
        aliases.add(key)
        return {"occupation_id": occupation_id, "title": title}
    if kind == "related":
        code = related_code(row)
        if code is None:
            return None
        key = (occupation_id, code)
        if key in related:
            return {}
        related.add(key)
        return {"occupation_id": occupation_id, "related_onet_soc_code": code,
                "related_title": row.get("Related Title"), "attributes": row}
    name = descriptor_name(row)
    if not name:
        return None
    key = tuple(sorted(row.items()))
    if key in seen_descriptors:
        return {}
    seen_descriptors.add(key)
    return {
        "occupation_id": occupation_id, "category": kind, "name": name,
        "element_id": descriptor_element_id(row), "scale": row.get("Scale ID"),
        "rating": descriptor_rating(row, member.filename), "source": "O*NET", "attributes": row,
    }
