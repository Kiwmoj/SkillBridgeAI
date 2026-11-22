"""Portfolio Builder: private image and PDF storage, metadata, organisation, and optional AI review."""
import io
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import BadRequest, NotFoundError, PayloadTooLarge
from apps.backend.models import Project, User
from apps.backend.repositories import portfolio as repository
from apps.backend.services.ai.grounded import generate_from_image

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_EDGE = 1800
REVIEW_PROMPT = (
    "Review this student portfolio image for clarity, visual hierarchy, accessibility, "
    "project readability, and presentation. Clearly distinguish what is visible in the "
    "image from inferences. Provide constructive, specific educational feedback."
)


def sanitize_image(content: bytes) -> bytes:
    """Re-encode the first frame as a bounded, metadata-free PNG on a white background."""
    if len(content) > MAX_UPLOAD_BYTES:
        raise PayloadTooLarge("Portfolio image exceeds 10 MB")
    try:
        with Image.open(io.BytesIO(content), formats=["PNG", "JPEG", "WEBP", "GIF"]) as image:
            if image.width * image.height > MAX_PIXELS:
                raise PayloadTooLarge("Portfolio images must be at most 20 megapixels.")
            image = ImageOps.exif_transpose(image)
            image.thumbnail((MAX_EDGE, MAX_EDGE))
            picture = image.convert("RGBA")
            rgb = Image.new("RGB", picture.size, "white")
            rgb.paste(picture, mask=picture.getchannel("A"))
            sanitized = io.BytesIO()
            rgb.save(sanitized, format="PNG")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise BadRequest("Upload a valid PDF, PNG, JPEG, WEBP, or GIF file.") from None
    return sanitized.getvalue()


def validate_pdf(content: bytes) -> bytes:
    """Accept only files that really are PDFs: magic header and a closing marker, within the size limit."""
    if len(content) > MAX_UPLOAD_BYTES:
        raise PayloadTooLarge("Portfolio file exceeds 10 MB")
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
        raise BadRequest("Upload a valid PDF, PNG, JPEG, WEBP, or GIF file.")
    return content


def store_upload(db: Session, user: User, filename: str | None, content: bytes, upload_dir: Path):
    is_pdf = content.startswith(b"%PDF-")
    stored_bytes = validate_pdf(content) if is_pdf else sanitize_image(content)
    extension, mime = (".pdf", "application/pdf") if is_pdf else (".png", "image/png")
    upload_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    target = upload_dir / stored_name
    target.write_bytes(stored_bytes)
    item = repository.add_item(
        db, user.id, Path((filename or "portfolio").replace("\\", "/")).name[:255], stored_name, mime,
    )
    try:
        db.commit()
    except SQLAlchemyError:
        target.unlink(missing_ok=True)
        raise
    db.refresh(item)
    return item


def list_items(db: Session, user_id: int) -> list[dict]:
    return [serialize(item) for item in repository.list_items(db, user_id)]


def serialize(item) -> dict:
    return {
        "id": item.id,
        "filename": item.filename,
        "title": item.title or Path(item.filename).stem,
        "description": item.description,
        "tags": [tag.strip() for tag in (item.tags or "").split(",") if tag.strip()],
        "project_id": item.project_id,
        "featured": bool(item.featured),
        "evaluation": item.evaluation,
        "created_at": item.created_at.isoformat(),
        "mime_type": item.mime_type,
        "kind": "pdf" if item.mime_type == "application/pdf" else "image",
        "file_url": f"/api/v1/portfolio/{item.id}/file",
    }


def update_details(db: Session, user_id: int, portfolio_id: int, fields: dict) -> dict:
    item = repository.get_item(db, user_id, portfolio_id)
    if not item:
        raise NotFoundError("Portfolio item not found")
    project_id = fields.get("project_id")
    if project_id is not None and not db.query(Project).filter_by(id=project_id, user_id=user_id).first():
        raise NotFoundError("Project not found")
    if "tags" in fields and fields["tags"] is not None:
        fields["tags"] = ", ".join(tag.strip() for tag in fields["tags"] if tag.strip())[:255]
    for key in ("title", "description"):
        if key in fields and isinstance(fields[key], str):
            fields[key] = fields[key].strip() or None
    for key, value in fields.items():
        if key == "featured" and value is None:
            continue
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return serialize(item)


def image_path(db: Session, user_id: int, portfolio_id: int, upload_dir: Path) -> Path:
    item = repository.get_item(db, user_id, portfolio_id)
    if not item:
        raise NotFoundError("Portfolio item not found")
    path = upload_dir / Path(item.stored_path).name
    if not path.is_file():
        raise NotFoundError("Stored portfolio image is unavailable")
    return path


def delete_item(db: Session, user_id: int, portfolio_id: int, upload_dir: Path) -> None:
    item = repository.get_item(db, user_id, portfolio_id)
    if not item:
        raise NotFoundError("Portfolio item not found")
    stored = upload_dir / Path(item.stored_path).name
    db.delete(item)
    db.commit()
    stored.unlink(missing_ok=True)


def review(db: Session, user: User, portfolio_id: int, upload_dir: Path) -> dict:
    item = repository.get_item(db, user.id, portfolio_id)
    if not item:
        raise NotFoundError("Portfolio item not found")
    if item.mime_type == "application/pdf":
        raise BadRequest("AI review currently supports images only. PDFs are stored and can be viewed or downloaded.")
    try:
        image_bytes = (upload_dir / Path(item.stored_path).name).read_bytes()
    except FileNotFoundError:
        raise NotFoundError("Stored portfolio image is unavailable") from None
    evaluation = generate_from_image(db, user, "portfolio_review", REVIEW_PROMPT, image_bytes, item.mime_type)
    item.evaluation = evaluation
    db.commit()
    return {"id": item.id, "evaluation": evaluation}
