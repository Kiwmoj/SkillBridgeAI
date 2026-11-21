import csv
import io
import json
import math
import re
import zipfile
from collections import Counter
from pathlib import PurePosixPath
from typing import BinaryIO

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from backend.models import (
    AlternateTitle, DatasetVersion, Descriptor, Occupation, RelatedOccupation, TrainingHistory,
)

ONET_URL = "https://www.onetcenter.org/database.html"
ONET_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
ONET_CREDIT = "O*NET® Database, U.S. Department of Labor, Employment and Training Administration"
OCCUPATION_CODE = re.compile(r"\d{2}-\d{4}\.\d{2}")
RATED_SKILL_CATEGORIES = ("Skills", "Essential Skills", "Transferable Skills", "Knowledge", "Abilities")
MAX_UNCOMPRESSED = 750 * 1024 * 1024
FILE_CATEGORIES = {
    "skills": "Skills",
    "essentialskills": "Essential Skills",
    "transferableskills": "Transferable Skills",
    "knowledge": "Knowledge",
    "abilities": "Abilities",
    "educationtrainingandexperience": "Education",
    "education": "Education",
    "trainingandexperience": "Training and Experience",
    "jobzones": "Job Zones",
    "workactivities": "Work Activities",
    "detailedworkactivities": "Detailed Work Activities",
    "taskstodwas": "Detailed Work Activities",
    "tasks": "Tasks",
    "taskstatements": "Tasks",
    "taskratings": "Task Ratings",
    "emergingtasks": "Emerging Tasks",
    "workstyles": "Work Styles",
    "workcontext": "Work Context",
    "technologyskills": "Technology Skills",
    "softwareskills": "Technology Skills",
    "interests": "Interests",
    "careerinteresttypes": "Interests",
    "specificinterestareas": "Specific Interest Areas",
    "workvalues": "Work Values",
}
TITLE_FILES = {"alternatetitles", "jobtitles", "sampleofreportedtitles"}
VERSION_PATTERN = re.compile(r"^[\w .-]{1,32}$")


class OnetImportError(RuntimeError):
    pass


def _members(archive: zipfile.ZipFile):
    entries = archive.infolist()
    if len(entries) > 500 or sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED:
        raise OnetImportError("The unpacked archive exceeds the supported size.")
    for entry in entries:
        name = PurePosixPath(entry.filename.replace("\\", "/"))
        if not entry.is_dir() and name.suffix.lower() in {".csv", ".txt"}:
            yield re.sub(r"[^a-z0-9]+", "", name.stem.lower()), entry, name.suffix.lower()


def _rows(archive, entry, extension):
    with archive.open(entry) as stream:
        reader = csv.DictReader(
            io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""),
            delimiter="\t" if extension == ".txt" else ",",
        )
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise OnetImportError(f"Malformed row {reader.line_num} in {PurePosixPath(entry.filename).name}.")
            yield {key.strip(): value.strip() for key, value in row.items() if value.strip()}


def _code(row):
    return row.get("O*NET-SOC Code") or row.get("onet_soc_code", "")


def _add_batch(db, table, batch):
    if batch:
        db.execute(insert(table), batch)
        batch.clear()


def import_onet_zip(db: Session, path: str | BinaryIO, version: str) -> dict:
    """Replace the imported reference rows for this release, preserving occupation IDs."""
    try:
        with zipfile.ZipFile(path) as archive:
            return _import_archive(db, archive, version)
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


def _import_archive(db: Session, archive: zipfile.ZipFile, version: str) -> dict:
    files = list(_members(archive))
    primary = [(entry, extension) for name, entry, extension in files if name == "occupationdata"]
    if len(primary) != 1:
        raise OnetImportError("The archive must contain exactly one Occupation Data CSV or text file.")
    release_notes = next((entry for name, entry, _ in files if name == "readme"), None)
    if release_notes:
        with archive.open(release_notes) as stream:
            header = stream.read(1024).decode("utf-8-sig", errors="replace")
        declared = re.search(r"O\*NET[®]?\s+([\d.]+)\s+Database", header)
        if declared and version not in ("user-supplied", declared[1]):
            raise OnetImportError(f"The archive identifies itself as version {declared[1]}, not {version}.")
        if declared:
            version = declared[1]

    saved = {item.onet_soc_code: item for item in db.scalars(select(Occupation))}
    loaded = {}
    for row in _rows(archive, *primary[0]):
        code, title = _code(row), row.get("Title") or row.get("title", "")
        if not OCCUPATION_CODE.fullmatch(code) or not title or len(title) > 255 or code in loaded:
            raise OnetImportError("Occupation Data contains an invalid or duplicate occupation.")
        occupation = saved.get(code)
        if occupation is None:
            occupation = Occupation(onet_soc_code=code)
            db.add(occupation)
        occupation.title = title
        occupation.description = row.get("Description") or row.get("description")
        occupation.dataset_version = version
        loaded[code] = occupation
    if not loaded:
        raise OnetImportError("Occupation Data is empty.")
    db.flush()
    ids = {code: item.id for code, item in loaded.items()}

    # Remove old reference details for updated codes without deleting saved careers.
    occupation_ids = select(Occupation.id).where(Occupation.dataset_version == version)
    for table in (AlternateTitle, Descriptor, RelatedOccupation):
        db.execute(delete(table).where(table.occupation_id.in_(occupation_ids)))
    for code, occupation in saved.items():
        if code not in loaded:
            occupation.dataset_version = None

    aliases = set()
    related = set()
    file_counts = Counter()
    counts = Counter(occupations=len(ids), alternate_titles=0, descriptors=0, related_occupations=0, skipped_rows=0)
    for file, entry, extension in files:
        category = FILE_CATEGORIES.get(file)
        if file in TITLE_FILES:
            table = AlternateTitle
        elif file == "relatedoccupations":
            table = RelatedOccupation
        elif category is not None:
            table = Descriptor
        else:
            continue
        batch = []
        seen_descriptors = set()
        file_counts[PurePosixPath(entry.filename).name] = 0
        for row in _rows(archive, entry, extension):
            occupation_id = ids.get(_code(row))
            if occupation_id is None:
                counts["skipped_rows"] += 1
                continue
            record = {"occupation_id": occupation_id}
            if table is AlternateTitle:
                title = row.get("Job Title") or row.get("Alternate Title") or row.get("Reported Job Title")
                if not title or len(title) > 255:
                    counts["skipped_rows"] += 1
                    continue
                key = (occupation_id, title.casefold())
                if key in aliases:
                    continue
                aliases.add(key)
                record["title"] = title
                counts["alternate_titles"] += 1
            elif table is RelatedOccupation:
                code = row.get("Related O*NET-SOC Code", "")
                if not OCCUPATION_CODE.fullmatch(code):
                    counts["skipped_rows"] += 1
                    continue
                key = (occupation_id, code)
                if key in related:
                    continue
                related.add(key)
                record.update(related_onet_soc_code=code, related_title=row.get("Related Title"), attributes=row)
                counts["related_occupations"] += 1
            else:
                name = next((row[key] for key in (
                    "Workplace Example", "Example", "Technology", "DWA Element Name",
                    "DWA Title", "Element Name", "Task", "Job Zone", "Commodity Title",
                ) if key in row), "")
                if not name:
                    counts["skipped_rows"] += 1
                    continue
                key = tuple(sorted(row.items()))
                if key in seen_descriptors:
                    continue
                seen_descriptors.add(key)
                try:
                    value = float(row["Data Value"]) if "Data Value" in row else None
                except ValueError as exc:
                    raise OnetImportError(f"Invalid numeric rating in {PurePosixPath(entry.filename).name}.") from exc
                if value is not None and not math.isfinite(value):
                    raise OnetImportError("Non-finite O*NET rating.")
                record.update(
                    category=category, name=name,
                    element_id=next((row[key] for key in (
                        "DWA Element ID", "DWA ID", "Element ID", "Task ID", "Commodity Code",
                        "Original Task ID",
                    ) if key in row), ""),
                    scale=row.get("Scale ID"), rating=value, source="O*NET", attributes=row,
                )
                counts["descriptors"] += 1
            batch.append(record)
            file_counts[PurePosixPath(entry.filename).name] += 1
            if len(batch) == 2000:
                _add_batch(db, table, batch)
        _add_batch(db, table, batch)
    return {**counts, "version": version, "files": dict(file_counts), "source": ONET_URL}
