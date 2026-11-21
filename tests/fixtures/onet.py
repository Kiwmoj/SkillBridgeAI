"""A small synthetic O*NET archive in the legacy tab-delimited layout, covering ten industries."""
import zipfile
from pathlib import Path

OCCUPATIONS = [
    ("11-1011.00", "Chief Executives", "Lead organizations", "Business"),
    ("25-2011.00", "Preschool Teachers", "Teach young children", "Education"),
    ("29-1141.00", "Registered Nurses", "Care for patients", "Healthcare"),
    ("17-2051.00", "Civil Engineers", "Design infrastructure", "Engineering"),
    ("27-1024.00", "Graphic Designers", "Create visual communications", "Arts"),
    ("51-4121.00", "Welders", "Join metal components", "Trades"),
    ("19-2041.00", "Environmental Scientists", "Study environmental systems", "Science"),
    ("41-3031.00", "Securities Traders", "Trade financial instruments", "Finance"),
    ("35-1011.00", "Chefs", "Direct food preparation", "Hospitality"),
    ("45-2011.00", "Agricultural Inspectors", "Inspect agricultural operations", "Agriculture"),
]


def make_onet_archive(directory: Path) -> tuple[Path, list[tuple[str, str, str, str]]]:
    archive = directory / "onet.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(
            "Database/Occupation Data.txt",
            "O*NET-SOC Code\tTitle\tDescription\n"
            + "\n".join(f"{code}\t{title}\t{description}" for code, title, description, _industry in OCCUPATIONS),
        )
        z.writestr(
            "Database/Alternate Titles.txt",
            "O*NET-SOC Code\tAlternate Title\n29-1141.00\tNurse\n17-2051.00\tStructural Engineer",
        )
        z.writestr(
            "Database/Skills.txt",
            "O*NET-SOC Code\tElement ID\tElement Name\tData Value\tScale ID\n"
            "29-1141.00\t2-A\tActive Listening\t4.5\tLV\n"
            "17-2051.00\t2-B\tMathematics\t4.2\tLV",
        )
        z.writestr(
            "Database/Tasks.txt",
            "O*NET-SOC Code\tTask ID\tTask\n29-1141.00\t1\tAssess patient needs\n17-2051.00\t2\tReview structural drawings",
        )
        z.writestr(
            "Database/Related Occupations.txt",
            "O*NET-SOC Code\tRelated O*NET-SOC Code\tRelated Title\n29-1141.00\t29-1122.00\tOccupational Therapists",
        )
    return archive, OCCUPATIONS
