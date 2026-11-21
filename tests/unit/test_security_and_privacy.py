from datetime import datetime, timedelta, timezone

import jwt
import pytest

from apps.backend.core import security
from apps.backend.services.community.privacy import contains_identifiers, sanitize_for_training
from apps.backend.services.training.pipeline import stable_hash


def test_password_hashes_are_salted_and_verified():
    first, second = security.hash_password("correct horse"), security.hash_password("correct horse")
    assert first != second and first.startswith("$argon2")
    assert security.verify_password("correct horse", first)
    assert not security.verify_password("wrong", first)
    assert not security.verify_password("anything", "not-a-hash")


def test_tokens_round_trip_and_reject_bad_claims():
    token = security.create_token(7, 3)
    assert security.decode_token(token) == (7, 3)
    now = datetime.now(timezone.utc)
    missing_version = jwt.encode({"sub": "7", "iat": now, "exp": now + timedelta(minutes=5), "iss": "skillbridge"},
                                 security.SECRET, "HS256")
    wrong_issuer = jwt.encode({"sub": "7", "v": 3, "iat": now, "exp": now + timedelta(minutes=5), "iss": "other"},
                              security.SECRET, "HS256")
    for bad in (missing_version, wrong_issuer, token + "x", ""):
        with pytest.raises(ValueError):
            security.decode_token(bad)


def test_recovery_digest_is_stable_and_whitespace_insensitive():
    assert security.recovery_digest(" code ") == security.recovery_digest("code")
    assert len(security.recovery_digest("code")) == 64


def test_identifiers_are_redacted_before_training():
    text = "Email me at student@example.com or call (555) 123-4567; SSN 123-45-6789."
    sanitized = sanitize_for_training(text)
    assert "[REDACTED_EMAIL]" in sanitized and "[REDACTED_PHONE]" in sanitized and "[REDACTED_SSN]" in sanitized
    assert "example.com" not in sanitized and "4567" not in sanitized
    assert contains_identifiers("fine text", text) and not contains_identifiers("fine text", None)
    assert sanitize_for_training(None) == ""
    assert stable_hash("a") == stable_hash("a") != stable_hash("b")
