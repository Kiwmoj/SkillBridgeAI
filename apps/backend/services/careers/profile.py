"""Full career profiles assembled from imported official O*NET data.

Everything here is a reformatting of O*NET records; nothing is generated or estimated.
"""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError
from apps.backend.models import Descriptor, Occupation, OnetCategory, OnetElement, OnetJobZone
from apps.backend.repositories import occupations as repository
from apps.backend.services.careers.explorer import ATTRIBUTION, is_reported, occupation_summary

RIASEC_ORDER = ("Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional")
SKILL_CATEGORIES = ("Skills", "Essential Skills", "Transferable Skills")
EDUCATION_ELEMENT = "2.D.1"


def _top_rated(rows: list[Descriptor], categories: tuple[str, ...], limit: int) -> list[dict]:
    """Highest importance-scale descriptors, one entry per name."""
    best: dict[str, Descriptor] = {}
    for row in rows:
        if row.category in categories and row.scale == "IM" and row.rating is not None and is_reported(row):
            key = row.name.casefold()
            if key not in best or (row.rating or 0) > (best[key].rating or 0):
                best[key] = row
    ranked = sorted(best.values(), key=lambda d: d.rating or 0, reverse=True)[:limit]
    return [{"name": d.name, "element_id": d.element_id, "importance": d.rating, "category": d.category} for d in ranked]


def _level_lookup(rows: list[Descriptor], category: str) -> dict[str, float]:
    return {d.element_id: d.rating for d in rows
            if d.category == category and d.scale == "LV" and d.rating is not None}


def education_pathway(db: Session, rows: list[Descriptor]) -> list[dict]:
    labels = {c.category: c.description for c in db.query(OnetCategory).filter_by(element_id=EDUCATION_ELEMENT,
                                                                                  scale_id="RL")}
    levels = []
    for row in rows:
        if row.category == "Education" and row.element_id == EDUCATION_ELEMENT and row.rating:
            try:
                number = int(row.attributes.get("Category", ""))
            except ValueError:
                continue
            levels.append({"level": number, "label": labels.get(number, f"Education category {number}"),
                           "percent_of_workers": round(row.rating, 1)})
    return sorted([level for level in levels if level["percent_of_workers"] >= 1],
                  key=lambda item: item["percent_of_workers"], reverse=True)


def job_zone(db: Session, rows: list[Descriptor]) -> dict | None:
    zone_row = next((d for d in rows if d.category == "Job Zones"), None)
    if zone_row is None:
        return None
    try:
        zone = int(float(zone_row.name))
    except ValueError:
        return None
    # The reference table groups zones 1 and 2 under one entry keyed 2.
    reference = db.get(OnetJobZone, zone) or db.get(OnetJobZone, max(zone, 2))
    return {
        "zone": zone,
        "name": reference.name if reference else f"Job Zone {zone}",
        "experience": reference.experience if reference else None,
        "education": reference.education if reference else None,
        "training": reference.training if reference else None,
    }


def build_profile(db: Session, occupation_id: int) -> dict:
    occupation = repository.get_active(db, occupation_id)
    if not occupation:
        raise NotFoundError("Occupation not found")
    rows = db.query(Descriptor).filter_by(occupation_id=occupation_id).all()
    definitions = {
        e.element_id: e.description
        for e in db.query(OnetElement).filter(OnetElement.element_id.in_({d.element_id for d in rows if d.element_id}))
    }
    skill_levels = _level_lookup(rows, "Skills") | _level_lookup(rows, "Essential Skills")

    def with_definitions(items: list[dict]) -> list[dict]:
        for item in items:
            item["definition"] = definitions.get(item["element_id"])
            item["level"] = skill_levels.get(item["element_id"])
        return items

    interests = sorted(
        ({"name": d.name, "score": d.rating} for d in rows
         if d.category == "Interests" and d.scale == "OI" and d.name in RIASEC_ORDER and d.rating is not None),
        key=lambda item: item["score"] or 0, reverse=True,
    )
    tasks = [d for d in rows if d.category == "Tasks"]
    core_tasks = [d.name for d in tasks if d.attributes.get("Task Type") == "Core"] or [d.name for d in tasks]
    technology = [d for d in rows if d.category == "Technology Skills"]
    hot = [d.name for d in technology if d.attributes.get("Hot Technology") == "Y"]
    other_tools = [d.name for d in technology if d.attributes.get("Hot Technology") != "Y"]
    related = repository.related_occupations(db, occupation_id)
    codes = {item.related_onet_soc_code for item in related}
    local_ids = {o.onet_soc_code: o.id for o in db.query(Occupation).filter(
        Occupation.onet_soc_code.in_(codes), Occupation.dataset_version.is_not(None))} if codes else {}

    return {
        "attribution": ATTRIBUTION,
        "occupation": occupation_summary(occupation),
        "alternate_titles": [item.title for item in repository.alternate_titles(db, occupation_id)][:15],
        "interests": interests,
        "skills": with_definitions(_top_rated(rows, SKILL_CATEGORIES, 12)),
        "knowledge": with_definitions(_top_rated(rows, ("Knowledge",), 10)),
        "abilities": with_definitions(_top_rated(rows, ("Abilities",), 8)),
        "work_activities": with_definitions(_top_rated(rows, ("Work Activities",), 8)),
        "tasks": core_tasks[:15],
        "technology": {"in_demand": hot[:15], "other": other_tools[:15]},
        "education": education_pathway(db, rows),
        "job_zone": job_zone(db, rows),
        "related_occupations": [
            {"onet_soc_code": item.related_onet_soc_code, "title": item.related_title,
             "id": local_ids.get(item.related_onet_soc_code)}
            for item in related
        ][:12],
    }
