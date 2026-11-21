import argparse
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from apps.backend.database import SessionLocal
from apps.backend.services.careers.onet_import import OnetImportError, import_onet_zip, register_import
from packages.onet.validators import VERSION_PATTERN


def main():
    parser = argparse.ArgumentParser(description="Load an official O*NET ZIP into this server's database.")
    parser.add_argument("archive", type=Path, help="official O*NET CSV or text ZIP")
    parser.add_argument("--version", default="user-supplied",
                        help="expected release such as 31.0; by default the archive's own version is used")
    args = parser.parse_args()
    if args.archive.suffix.lower() != ".zip" or not args.archive.is_file():
        parser.exit(1, "Provide the official O*NET ZIP file.\n")
    if not VERSION_PATTERN.fullmatch(args.version):
        parser.exit(1, "Use a version label of up to 32 letters, digits, spaces, dots or dashes.\n")
    with SessionLocal() as db:
        try:
            result = import_onet_zip(db, str(args.archive), args.version)
            register_import(db, result)
            db.commit()
        except OnetImportError as exc:
            db.rollback()
            parser.exit(1, f"{exc}\n")
        except SQLAlchemyError as exc:
            db.rollback()
            parser.exit(1, f"Database error: {exc}\nCheck DATABASE_URL and run 'python -m alembic upgrade head'.\n")
    print(
        f"Imported O*NET {result['version']}: {result['occupations']} occupations, "
        f"{result['alternate_titles']} alternate titles, {result['descriptors']} descriptors, "
        f"{result['related_occupations']} related occupations, {result['skipped_rows']} skipped rows."
    )


if __name__ == "__main__":
    main()
