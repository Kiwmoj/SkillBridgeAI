import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal
from backend.models import Profile, User
from backend.schemas import RegisterRequest
from backend.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create a SkillBridge administrator on this server.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    password = getpass("New administrator password: ")
    if password != getpass("Confirm password: "):
        parser.exit(1, "Passwords do not match.\n")
    try:
        account = RegisterRequest(email=args.email, name=args.name, password=password)
    except ValidationError:
        parser.exit(1, "Use a valid email, nonempty name, and a password of 8 to 128 characters.\n")
    with SessionLocal() as db:
        user = User(
            email=account.email.lower(), name=account.name.strip(),
            password_hash=hash_password(account.password), role="admin",
        )
        user.profile = Profile()
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            parser.exit(1, "An account with this email already exists.\n")
    print("Administrator created.")


if __name__ == "__main__":
    main()
