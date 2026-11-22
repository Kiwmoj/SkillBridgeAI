from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.core import config
from apps.backend.core.exceptions import NotFoundError
from apps.backend.repositories import portfolio as repository
from apps.backend.schemas.portfolio import PortfolioReviewRequest
from apps.backend.services.portfolio import images

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/upload")
def upload_portfolio(user: CurrentUser, db: DbSession, file: UploadFile = File(...)):
    content = file.file.read(images.MAX_UPLOAD_BYTES + 1)
    item = images.store_upload(db, user, file.filename, content, config.settings.upload_dir)
    return {"id": item.id, "filename": item.filename}


@router.get("")
def list_portfolios(user: CurrentUser, db: DbSession):
    return images.list_items(db, user.id)


@router.get("/{portfolio_id}/file")
def portfolio_file(portfolio_id: int, user: CurrentUser, db: DbSession):
    item = repository.get_item(db, user.id, portfolio_id)
    if item is None:
        raise NotFoundError("Portfolio item not found")
    path = images.image_path(db, user.id, portfolio_id, config.settings.upload_dir)
    # nosniff + sandbox keep an uploaded PDF from running anything in the app's origin.
    return FileResponse(path, media_type=item.mime_type, filename=item.filename, content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"})


@router.post("/{portfolio_id}/evaluate")
def evaluate_portfolio(portfolio_id: int, request: PortfolioReviewRequest, user: CurrentUser, db: DbSession):
    return images.review(db, user, portfolio_id, config.settings.upload_dir)
