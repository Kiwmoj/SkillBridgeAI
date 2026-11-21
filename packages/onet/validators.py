"""Validation rules for O*NET identifiers and values."""
import math
import re

OCCUPATION_CODE = re.compile(r"\d{2}-\d{4}\.\d{2}")
VERSION_PATTERN = re.compile(r"^[\w .-]{1,32}$")
DECLARED_VERSION = re.compile(r"O\*NET[®]?\s+([\d.]+)\s+Database")
MAX_TITLE_LENGTH = 255


def is_occupation_code(value: str) -> bool:
    return bool(OCCUPATION_CODE.fullmatch(value))


def is_version_label(value: str) -> bool:
    return bool(VERSION_PATTERN.fullmatch(value))


def is_title(value: str | None) -> bool:
    return bool(value) and len(value or "") <= MAX_TITLE_LENGTH


def parse_rating(value: str | None) -> float | None:
    """Convert a Data Value cell to a finite float; raise ValueError for anything else."""
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite O*NET rating.")
    return number
