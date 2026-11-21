from fastapi import APIRouter, File, UploadFile

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.core import config
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


@router.post("/{portfolio_id}/evaluate")
def evaluate_portfolio(portfolio_id: int, request: PortfolioReviewRequest, user: CurrentUser, db: DbSession):
    return images.review(db, user, portfolio_id, config.settings.upload_dir)
