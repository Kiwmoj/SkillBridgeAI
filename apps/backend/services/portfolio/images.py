"""Private portfolio image storage and AI review."""
import io
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import BadRequest, NotFoundError, PayloadTooLarge
from apps.backend.models import User
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
        raise BadRequest("Upload a valid PNG, JPEG, WEBP, or GIF image.") from None
    return sanitized.getvalue()


def store_upload(db: Session, user: User, filename: str | None, content: bytes, upload_dir: Path):
    sanitized = sanitize_image(content)
    upload_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.png"
    target = upload_dir / stored_name
    target.write_bytes(sanitized)
    item = repository.add_item(
        db, user.id, Path((filename or "portfolio").replace("\\", "/")).name[:255], stored_name, "image/png",
    )
    try:
        db.commit()
    except SQLAlchemyError:
        target.unlink(missing_ok=True)
        raise
    db.refresh(item)
    return item


def list_items(db: Session, user_id: int) -> list[dict]:
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "evaluation": item.evaluation,
            "created_at": item.created_at.isoformat(),
        }
        for item in repository.list_items(db, user_id)
    ]


def review(db: Session, user: User, portfolio_id: int, upload_dir: Path) -> dict:
    item = repository.get_item(db, user.id, portfolio_id)
    if not item:
        raise NotFoundError("Portfolio item not found")
    try:
        image_bytes = (upload_dir / Path(item.stored_path).name).read_bytes()
    except FileNotFoundError:
        raise NotFoundError("Stored portfolio image is unavailable") from None
    evaluation = generate_from_image(db, user, "portfolio_review", REVIEW_PROMPT, image_bytes, item.mime_type)
    item.evaluation = evaluation
    db.commit()
    return {"id": item.id, "evaluation": evaluation}
