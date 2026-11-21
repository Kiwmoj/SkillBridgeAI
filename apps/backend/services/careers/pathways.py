"""Level-aware career guidance: education pathways, getting-started advice and level-matched career suggestions."""
from sqlalchemy.orm import Session

from apps.backend.models import Descriptor, Occupation
from apps.backend.services.levels import LEVELS, normalize

UNIVERSITY = ("bachelor", "master", "doctoral", "post-doctoral", "first professional", "professional")
COLLEGE_OR_VOCATIONAL = ("associate", "post-secondary", "some college", "certificate")
ON_THE_JOB = ("high school", "less than high school", "no formal")

GETTING_STARTED = {
    "beginner": [
        "You do not need any prior experience. Start by reading what this job actually involves.",
        "Pick one small skill from the roadmap and spend 20 to 30 minutes on it today.",
        "Ask someone who does this job one question, or watch a day-in-the-life video.",
    ],
    "intermediate": [
        "Compare your current skills with this career in the Skill Gap Analyzer to find what to work on next.",
        "Build one small project that mirrors a real task from this job and add it to your portfolio.",
        "Look for a certification, short course or apprenticeship that fills your biggest gap.",
    ],
    "advanced": [
        "Aim at the highest-importance skills and pick a specialization where you can stand out.",
        "Take on a capstone project with real constraints (time, quality, users) and document the trade-offs.",
        "Look at senior-level credentials, mentoring or leading projects to demonstrate expertise.",
    ],
}


def _group(label: str) -> str | None:
    """Each education level belongs to exactly one group (checked in order) so shares never double count."""
    text = label.lower()
    for name, keywords in (("university", UNIVERSITY), ("college", COLLEGE_OR_VOCATIONAL), ("on_the_job", ON_THE_JOB)):
        if any(keyword in text for keyword in keywords):
            return name
    return None


def _shares(education: list[dict]) -> dict[str, float]:
    totals = {"university": 0.0, "college": 0.0, "on_the_job": 0.0}
    for item in education:
        group = _group(item["label"])
        if group:
            totals[group] += item["percent_of_workers"]
    return {key: round(value, 1) for key, value in totals.items()}


def pathways(profile: dict) -> list[dict]:
    """Five ways into a career. The first three use O*NET worker education data; the rest are general advice."""
    education = profile["education"]
    zone = (profile["job_zone"] or {}).get("zone")
    share = _shares(education)
    have_data = bool(education)
    items = [
        ("university", "University or college degree", share["university"],
         "A bachelor's degree or higher, usually 4+ years of study."),
        ("vocational", "Vocational, technical or community college", share["college"],
         "Shorter programs (certificates or associate degrees) focused on job skills."),
        ("apprenticeship", "Apprenticeship or on-the-job training", share["on_the_job"],
         "Earn while you learn alongside experienced workers. Search official listings under Opportunities."),
    ]
    result = [
        {"id": key, "label": label, "summary": summary, "percent_of_workers": pct if have_data else None,
         "source": "O*NET worker education data" if have_data else "General guidance",
         "most_common": have_data and pct == max(share.values()) and pct > 0}
        for key, label, pct, summary in items
    ]
    result.append({"id": "certification", "label": "Professional certification", "percent_of_workers": None,
                   "summary": "Employers in many fields recognise industry certifications. Check which exist for this "
                              "career with the official directories under Opportunities.",
                   "source": "General guidance (not from O*NET)", "most_common": False})
    result.append({"id": "self_learning", "label": "Self-learning and projects", "percent_of_workers": None,
                   "summary": "Learn at your own pace with the Learning roadmap and build portfolio projects. "
                              "Some careers also require a license or degree, so confirm requirements first.",
                   "source": "General guidance (not from O*NET)", "most_common": False})
    if zone:
        result[0]["note"] = f"Job Zone {zone}: {profile['job_zone'].get('education') or ''}".strip()
    return result


def getting_started(level: str) -> list[str]:
    return GETTING_STARTED[normalize(level)]


def recommended(db: Session, level: str, limit: int = 12) -> list[dict]:
    """Careers whose O*NET Job Zone (amount of preparation needed) fits the learner's level."""
    zones = {str(z) for z in LEVELS[normalize(level)]["job_zones"]}
    rows = (
        db.query(Occupation, Descriptor.name)
        .join(Descriptor, Descriptor.occupation_id == Occupation.id)
        .filter(Occupation.dataset_version.is_not(None), Descriptor.category == "Job Zones")
        .order_by(Occupation.title)
        .all()
    )
    matches = []
    for occupation, zone_name in rows:
        try:
            zone = str(int(float(zone_name)))
        except ValueError:
            continue
        if zone in zones:
            matches.append({"id": occupation.id, "title": occupation.title, "onet_soc_code": occupation.onet_soc_code,
                            "job_zone": int(zone)})
    # Spread suggestions across the alphabet instead of returning only titles starting with "A".
    step = max(1, len(matches) // limit)
    return matches[::step][:limit]
