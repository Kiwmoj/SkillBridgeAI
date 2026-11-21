"""Career Explorer: search, detail, comparison, saved and custom careers over imported O*NET data."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError, ValidationFailure
from apps.backend.models import Descriptor, Occupation
from apps.backend.repositories import occupations as repository
from packages.onet.constants import ATTRIBUTION_NOTICE, ONET_CREDIT, ONET_LICENSE, ONET_URL

ATTRIBUTION = {
    "credit": ONET_CREDIT, "source_url": ONET_URL, "license_url": ONET_LICENSE, "notice": ATTRIBUTION_NOTICE,
}


def occupation_summary(occupation: Occupation) -> dict:
    return {
        "id": occupation.id,
        "onet_soc_code": occupation.onet_soc_code,
        "title": occupation.title,
        "description": occupation.description,
        "dataset_version": occupation.dataset_version,
    }


def is_reported(descriptor: Descriptor) -> bool:
    """O*NET flags descriptors analysts consider not relevant or statistically unreliable."""
    return descriptor.attributes.get("Recommend Suppress") != "Y" and descriptor.attributes.get("Not Relevant") != "Y"


def search(db: Session, text: str, limit: int) -> list[dict]:
    query_text = text.strip()
    if not query_text:
        return []
    return [occupation_summary(item) for item in repository.search(db, query_text, limit)]


def detail(db: Session, occupation_id: int, category: str | None, offset: int, limit: int) -> dict:
    occupation = repository.get_active(db, occupation_id)
    if not occupation:
        raise NotFoundError("Occupation not found")
    descriptors = repository.descriptors(db, occupation_id, category, offset, limit)
    return {
        "attribution": ATTRIBUTION,
        "descriptor_count": repository.descriptor_count(db, occupation_id, category),
        "categories": repository.descriptor_categories(db, occupation_id),
        "occupation": occupation_summary(occupation),
        "alternate_titles": [item.title for item in repository.alternate_titles(db, occupation_id)],
        "related_occupations": [
            {"onet_soc_code": item.related_onet_soc_code, "title": item.related_title}
            for item in repository.related_occupations(db, occupation_id)
        ],
        "descriptors": [
            {
                "category": descriptor.category,
                "element_id": descriptor.element_id,
                "name": descriptor.name,
                "rating": descriptor.rating,
                "scale": descriptor.scale,
                "source": descriptor.source,
                "attributes": descriptor.attributes,
            }
            for descriptor in descriptors
        ],
    }


def compare(db: Session, occupation_ids: list[int]) -> dict:
    unique_ids = list(dict.fromkeys(occupation_ids))
    if len(unique_ids) < 2:
        raise ValidationFailure("Select at least two different occupations.")
    occupations = [repository.get_active(db, occupation_id) for occupation_id in unique_ids]
    found = [occupation for occupation in occupations if occupation is not None]
    if len(found) != len(unique_ids):
        raise NotFoundError("One or more occupations were not found")
    result = []
    for occupation in found:
        descriptors = [d for d in repository.top_importance_descriptors(db, occupation.id) if is_reported(d)]
        result.append({
            **occupation_summary(occupation),
            "top_descriptors": [
                {"category": d.category, "name": d.name, "rating": d.rating, "scale": d.scale}
                for d in descriptors[:20]
            ],
        })
    return {"source": "Official O*NET descriptors", "occupations": result}


def saved_careers(db: Session, user_id: int) -> list[Occupation]:
    return repository.saved_careers(db, user_id)


def save_career(db: Session, user_id: int, occupation_id: int) -> None:
    if not repository.get_active(db, occupation_id):
        raise NotFoundError("Occupation not found in the current import.")
    if repository.get_saved_career(db, user_id, occupation_id):
        return
    repository.add_saved_career(db, user_id, occupation_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not repository.get_saved_career(db, user_id, occupation_id):
            raise


def remove_saved_career(db: Session, user_id: int, occupation_id: int) -> None:
    repository.remove_saved_career(db, user_id, occupation_id)
    db.commit()


def create_custom_occupation(db: Session, user_id: int, title: str, industry: str | None, description: str | None):
    item = repository.add_custom_occupation(
        db, user_id, title.strip(), industry.strip() if industry else None, description.strip() if description else None,
    )
    db.commit()
    db.refresh(item)
    return item


def list_custom_occupations(db: Session, user_id: int):
    return repository.list_custom_occupations(db, user_id)


def resolve_occupation(db: Session, occupation_id: int | None, text: str | None) -> Occupation | None:
    """Find an imported occupation by ID, exact title/code, or the best search match."""
    if occupation_id:
        return repository.get_active(db, occupation_id)
    if not text or not text.strip():
        return None
    exact = repository.find_by_title_or_code(db, text.strip())
    if exact:
        return exact
    matches = repository.search(db, text.strip(), 1)
    return matches[0] if matches else None


def delete_custom_occupation(db: Session, user_id: int, occupation_id: int) -> None:
    item = repository.get_custom_occupation(db, user_id, occupation_id)
    if not item:
        raise NotFoundError("Custom occupation not found")
    db.delete(item)
    db.commit()
