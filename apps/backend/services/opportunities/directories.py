"""Official directories for opportunities and colleges, plus the user's saved records.

SkillBridge links to authoritative search directories; it does not scrape or republish listings.
"""
from urllib.parse import quote

from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError
from apps.backend.repositories import opportunities as repository
from apps.backend.schemas.opportunities import OpportunitySaveRequest


def official_directories(query: str) -> list[dict]:
    query_text = query.strip()
    if not query_text:
        return []
    encoded = quote(query_text, safe="")
    return [
        {
            "title": f"Occupation search directory: {query_text}",
            "organization": "O*NET OnLine",
            "url": f"https://www.onetonline.org/find/quick?s={encoded}",
            "details": "Search official occupational information. Verify current availability and deadlines directly.",
        },
        {
            "title": "College and program search directory",
            "organization": "U.S. Department of Education / College Scorecard",
            "url": "https://collegescorecard.ed.gov/search/",
            "details": "Compare education options and costs. This is not a live event or admission listing.",
        },
        {
            "title": f"Training directory: {query_text}",
            "organization": "CareerOneStop",
            "url": f"https://www.careeronestop.org/Toolkit/Training/find-training.aspx?keyword={encoded}",
            "details": "Find training resources. Eligibility and availability must be confirmed with providers.",
        },
        {
            "title": "Registered Apprenticeship Finder",
            "organization": "U.S. Department of Labor",
            "url": "https://www.apprenticeship.gov/apprenticeship-job-finder",
            "details": "Official directory. Search on the source site; listings are not fetched by SkillBridge.",
        },
    ]


def save(db: Session, user_id: int, request: OpportunitySaveRequest):
    item = repository.add_saved(
        db, user_id, request.title, request.organization, str(request.url) if request.url else None, request.details,
    )
    db.commit()
    db.refresh(item)
    return item


def list_saved(db: Session, user_id: int):
    return repository.list_saved(db, user_id)


def remove(db: Session, user_id: int, opportunity_id: int) -> None:
    item = repository.get_saved(db, user_id, opportunity_id)
    if not item:
        raise NotFoundError("Saved opportunity not found")
    db.delete(item)
    db.commit()


def update_status(db: Session, user_id: int, opportunity_id: int, application_status: str):
    item = repository.get_saved(db, user_id, opportunity_id)
    if not item:
        raise NotFoundError("Saved opportunity not found.")
    item.application_status = application_status
    db.commit()
    db.refresh(item)
    return item
