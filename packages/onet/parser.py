"""Read official O*NET ZIP archives (31.0 CSV layout or legacy tab-delimited text files).

The parser knows nothing about databases; it yields validated rows that an importer stores.
"""
import csv
import io
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath

from packages.onet.constants import (
    DESCRIPTOR_ELEMENT_COLUMNS,
    DESCRIPTOR_NAME_COLUMNS,
    FILE_CATEGORIES,
    MAX_MEMBERS,
    MAX_UNCOMPRESSED_BYTES,
    OCCUPATION_FILE,
    README_FILE,
    RELATED_FILE,
    TITLE_COLUMNS,
    TITLE_FILES,
)
from packages.onet.validators import DECLARED_VERSION, is_occupation_code, is_title, parse_rating

USER_SUPPLIED_VERSION = "user-supplied"


class OnetParseError(ValueError):
    pass


@dataclass(frozen=True)
class ArchiveMember:
    key: str
    entry: zipfile.ZipInfo
    extension: str

    @property
    def filename(self) -> str:
        return PurePosixPath(self.entry.filename.replace("\\", "/")).name

    @property
    def kind(self) -> str | None:
        """'titles', 'related', a descriptor category, or None when the file is not imported."""
        if self.key in TITLE_FILES:
            return "titles"
        if self.key == RELATED_FILE:
            return "related"
        return FILE_CATEGORIES.get(self.key)


@dataclass(frozen=True)
class OccupationRow:
    code: str
    title: str
    description: str | None


class OnetArchive:
    def __init__(self, archive: zipfile.ZipFile):
        self._archive = archive
        entries = archive.infolist()
        if len(entries) > MAX_MEMBERS or sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
            raise OnetParseError("The unpacked archive exceeds the supported size.")
        self.members: list[ArchiveMember] = []
        for entry in entries:
            name = PurePosixPath(entry.filename.replace("\\", "/"))
            if not entry.is_dir() and name.suffix.lower() in {".csv", ".txt"}:
                key = re.sub(r"[^a-z0-9]+", "", name.stem.lower())
                self.members.append(ArchiveMember(key, entry, name.suffix.lower()))

    def rows(self, member: ArchiveMember) -> Iterator[dict[str, str]]:
        with self._archive.open(member.entry) as stream:
            reader = csv.DictReader(
                io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""),
                delimiter="\t" if member.extension == ".txt" else ",",
            )
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise OnetParseError(f"Malformed row {reader.line_num} in {member.filename}.")
                yield {key.strip(): value.strip() for key, value in row.items() if value.strip()}

    def occupation_member(self) -> ArchiveMember:
        primary = [member for member in self.members if member.key == OCCUPATION_FILE]
        if len(primary) != 1:
            raise OnetParseError("The archive must contain exactly one Occupation Data CSV or text file.")
        return primary[0]

    def declared_version(self) -> str | None:
        readme = next((member for member in self.members if member.key == README_FILE), None)
        if readme is None:
            return None
        with self._archive.open(readme.entry) as stream:
            header = stream.read(1024).decode("utf-8-sig", errors="replace")
        match = DECLARED_VERSION.search(header)
        return match[1] if match else None

    def resolve_version(self, requested: str) -> str:
        """Prefer the version the archive declares; reject a conflicting explicit request."""
        declared = self.declared_version()
        if declared and requested not in (USER_SUPPLIED_VERSION, declared):
            raise OnetParseError(f"The archive identifies itself as version {declared}, not {requested}.")
        return declared or requested

    def occupations(self) -> Iterator[OccupationRow]:
        seen: set[str] = set()
        for row in self.rows(self.occupation_member()):
            code, title = row_code(row), row.get("Title") or row.get("title", "")
            if not is_occupation_code(code) or not is_title(title) or code in seen:
                raise OnetParseError("Occupation Data contains an invalid or duplicate occupation.")
            seen.add(code)
            yield OccupationRow(code, title, row.get("Description") or row.get("description"))
        if not seen:
            raise OnetParseError("Occupation Data is empty.")


def row_code(row: dict[str, str]) -> str:
    return row.get("O*NET-SOC Code") or row.get("onet_soc_code", "")


def alternate_title(row: dict[str, str]) -> str | None:
    title = next((row[column] for column in TITLE_COLUMNS if column in row), None)
    return title if is_title(title) else None


def related_code(row: dict[str, str]) -> str | None:
    code = row.get("Related O*NET-SOC Code", "")
    return code if is_occupation_code(code) else None


def descriptor_name(row: dict[str, str]) -> str:
    return next((row[column] for column in DESCRIPTOR_NAME_COLUMNS if column in row), "")


def descriptor_element_id(row: dict[str, str]) -> str:
    return next((row[column] for column in DESCRIPTOR_ELEMENT_COLUMNS if column in row), "")


def descriptor_rating(row: dict[str, str], filename: str) -> float | None:
    try:
        return parse_rating(row.get("Data Value"))
    except ValueError as exc:
        raise OnetParseError(f"Invalid numeric rating in {filename}.") from exc
