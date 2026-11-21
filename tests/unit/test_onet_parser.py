import io
import zipfile

import pytest

from packages.onet.parser import OnetArchive, OnetParseError, alternate_title, descriptor_rating, related_code
from packages.onet.validators import is_occupation_code, is_version_label, parse_rating


def build(files: dict[str, str]) -> OnetArchive:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
    buffer.seek(0)
    return OnetArchive(zipfile.ZipFile(buffer))


def test_validators():
    assert is_occupation_code("29-1141.00") and not is_occupation_code("29-1141") and not is_occupation_code("x")
    assert is_version_label("31.0") and is_version_label("user-supplied") and not is_version_label("a" * 33)
    assert parse_rating("4.25") == 4.25 and parse_rating(None) is None
    with pytest.raises(ValueError):
        parse_rating("inf")
    with pytest.raises(ValueError):
        parse_rating("high")


def test_csv_layout_version_and_member_kinds():
    archive = build({
        "db_31_0_csv/Read Me.txt": "O*NET 31.0 Database\n",
        "db_31_0_csv/occupation_data.csv": "O*NET-SOC Code,Title,Description\n29-1141.00,Registered Nurses,Care\n",
        "db_31_0_csv/essential_skills.csv": "O*NET-SOC Code,Element Name,Scale ID,Data Value\n29-1141.00,Listening,IM,4.5\n",
        "db_31_0_csv/job_titles.csv": "O*NET-SOC Code,Job Title\n29-1141.00,Nurse\n",
        "db_31_0_csv/related_occupations.csv": "O*NET-SOC Code,Related O*NET-SOC Code\n29-1141.00,29-1122.00\n",
        "db_31_0_csv/unknown_table.csv": "a,b\n1,2\n",
    })
    assert archive.declared_version() == "31.0"
    assert archive.resolve_version("user-supplied") == "31.0"
    assert archive.resolve_version("31.0") == "31.0"
    with pytest.raises(OnetParseError, match="identifies itself as version 31.0"):
        archive.resolve_version("30.1")
    kinds = {member.filename: member.kind for member in archive.members}
    assert kinds["essential_skills.csv"] == "Essential Skills"
    assert kinds["job_titles.csv"] == "titles" and kinds["related_occupations.csv"] == "related"
    assert kinds["unknown_table.csv"] is None
    rows = list(archive.occupations())
    assert rows[0].code == "29-1141.00" and rows[0].title == "Registered Nurses" and rows[0].description == "Care"


def test_legacy_tab_layout_and_row_helpers():
    archive = build({
        "Database/Occupation Data.txt": "O*NET-SOC Code\tTitle\tDescription\n11-1011.00\tChief Executives\tLead\n",
        "Database/Alternate Titles.txt": "O*NET-SOC Code\tAlternate Title\n11-1011.00\tCEO\n",
    })
    assert archive.declared_version() is None and archive.resolve_version("29.0") == "29.0"
    member = next(member for member in archive.members if member.kind == "titles")
    row = next(archive.rows(member))
    assert alternate_title(row) == "CEO"
    assert related_code({"Related O*NET-SOC Code": "bad"}) is None
    assert descriptor_rating({"Data Value": "3.5"}, "skills.csv") == 3.5
    with pytest.raises(OnetParseError, match="Invalid numeric rating in skills.csv"):
        descriptor_rating({"Data Value": "n/a"}, "skills.csv")


@pytest.mark.parametrize("files, message", [
    ({"a.csv": "x,y\n1,2\n"}, "exactly one Occupation Data"),
    ({"occupation_data.csv": "O*NET-SOC Code,Title\n", "b/occupation_data.csv": "O*NET-SOC Code,Title\n"},
     "exactly one Occupation Data"),
    ({"occupation_data.csv": "O*NET-SOC Code,Title\n"}, "is empty"),
    ({"occupation_data.csv": "O*NET-SOC Code,Title\n1-1,Bad\n"}, "invalid or duplicate"),
    ({"occupation_data.csv": "O*NET-SOC Code,Title\n29-1141.00,A\n29-1141.00,B\n"}, "invalid or duplicate"),
    ({"occupation_data.csv": "O*NET-SOC Code,Title\n29-1141.00,A,extra\n"}, "Malformed row"),
])
def test_invalid_archives_are_rejected(files, message):
    archive = build(files)
    with pytest.raises(OnetParseError, match=message):
        list(archive.occupations())
