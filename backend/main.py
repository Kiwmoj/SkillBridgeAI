from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import io
import logging
from pathlib import Path
from secrets import compare_digest, token_urlsafe
from threading import Lock
from time import monotonic
from typing import Optional
from urllib.parse import quote
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import delete, or_, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import configure_logging, settings
from backend.database import engine, get_db
from backend.models import (
    AIUsage,
    ApprovedKnowledge,
    CommunityContribution,
    CommunityPolicy,
    CustomOccupation,
    DatasetRecord,
    DatasetVersion,
    Descriptor,
    LearningActivity,
    ModelVersion,
    Occupation,
    AlternateTitle,
    Opportunity,
    Portfolio,
    Profile,
    Project,
    RelatedOccupation,
    ReviewHistory,
    Roadmap,
    SavedCareer,
    SkillAssessment,
    TrainingConsent,
    TrainingHistory,
    User,
)
from backend.schemas import (
    AIGenerateRequest,
    CareerCompareRequest,
    CONSENT_VERSION,
    ContributionReviewRequest,
    ContributionRequest,
    ContributionResponse,
    CustomOccupationRequest,
    DatasetBuildRequest,
    LearningActivityRequest,
    LoginRequest,
    ModelVersionRequest,
    OpportunitySaveRequest,
    OpportunityStatusRequest,
    PasswordConfirmation,
    PasswordResetRequest,
    PortfolioReviewRequest,
    ProfileRequest,
    ProjectRequest,
    ProjectUpdateRequest,
    RegisterRequest,
    RoadmapRequest,
    SkillAssessmentRequest,
    SkillGapRequest,
    TokenResponse,
    TrainingConsentRequest,
)
from backend.security import (
    DUMMY_PASSWORD_HASH,
    SECRET_CONFIGURED,
    create_token,
    decode_token,
    hash_password,
    recovery_digest,
    verify_password,
)
from backend.services.ai_providers import AIProviderError, AIService
from backend.services.onet_import import (
    ONET_CREDIT, ONET_LICENSE, ONET_URL, RATED_SKILL_CATEGORIES, OnetImportError, import_onet_zip,
    register_import,
)
from backend.services.retrieval import RetrievalService, hashed_embedding, source_context
from backend.services.training_pipeline import build_reviewed_dataset, invalidate_datasets, sanitize_for_training


configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
UPLOAD_DIR = settings.upload_dir
MAX_PORTFOLIO_UPLOAD = 10 * 1024 * 1024
MAX_ONET_UPLOAD = 500 * 1024 * 1024
SCHEMA_REVISION = "20261121_repair"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s %s (environment=%s, database=%s, ai_provider=%s)", app.title, app.version,
                settings.environment, settings.database_backend, settings.ai_provider)
    try:
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except SQLAlchemyError as exc:
        logger.error("Database connection failed during startup: %s", type(exc).__name__)
        raise RuntimeError("Check DATABASE_URL and run 'python -m alembic upgrade head'.") from exc
    if revision != SCHEMA_REVISION:
        logger.error("Database schema revision %r does not match the expected %r.", revision, SCHEMA_REVISION)
        raise RuntimeError("Run 'python -m alembic upgrade head' before starting SkillBridge AI.")
    if not settings.jwt_secret_configured:
        logger.warning("JWT_SECRET is not configured; sessions will expire when this process stops.")
    logger.info("Startup checks passed.")
    yield
    engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(title="SkillBridge AI", version="1.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

ai = AIService()
retrieval = RetrievalService()

_rate_lock = Lock()
_rate_windows: dict[str, list[float]] = {}
_onet_import_lock = Lock()


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    errors = [{"loc": error["loc"], "msg": error["msg"]} for error in exc.errors()]
    logger.info("Invalid request %s %s: %d validation error(s)", request.method, request.url.path, len(errors))
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(SQLAlchemyError)
async def database_failure(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "The database is unavailable. Try again shortly."})


@app.exception_handler(Exception)
async def unexpected_failure(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.middleware("http")
async def request_rate_limit(request: Request, call_next):
    if request.method != "POST":
        return await call_next(request)
    path = request.url.path
    if path.startswith("/auth/"):
        bucket, limit = "auth", 30
    elif path in {"/ai/generate", "/roadmaps", "/projects"} or (
        path.startswith("/portfolio/") and path.endswith("/evaluate")
    ):
        bucket, limit = "generation", 30
    elif path in {"/contributions", "/portfolio/upload"}:
        bucket, limit = "submission", 30
    else:
        return await call_next(request)
    key = f"{request.client.host if request.client else 'unknown'}:{bucket}"
    now = monotonic()
    with _rate_lock:
        for expired in [entry for entry, times in _rate_windows.items() if now - times[-1] >= 60]:
            del _rate_windows[expired]
        recent = [timestamp for timestamp in _rate_windows.get(key, []) if now - timestamp < 60]
        if len(recent) >= limit or (key not in _rate_windows and len(_rate_windows) >= 4096):
            retry_after = max(1, 60 - int(now - recent[0])) if recent else 60
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait before trying again."},
                headers={"Retry-After": str(retry_after)},
            )
        recent.append(now)
        _rate_windows[key] = recent
    return await call_next(request)


def utcnow():
    return datetime.now(timezone.utc)


def current_user(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        logger.info("Rejected unauthenticated request to %s %s", request.method, request.url.path)
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        user_id, session_version = decode_token(authorization.split(" ", 1)[1])
    except (ValueError, TypeError):
        logger.info("Rejected invalid or expired token on %s %s", request.method, request.url.path)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if not user or user.session_version != session_version:
        logger.info("Rejected revoked session on %s %s", request.method, request.url.path)
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def record_ai_usage(
    db: Session,
    user: User,
    feature: str,
    success: bool,
    started: float,
):
    latency_ms = max(0, int((monotonic() - started) * 1000))
    db.add(
        AIUsage(
            user_id=user.id,
            provider=ai.active,
            feature=feature,
            success=success,
            latency_ms=latency_ms,
        )
    )
    db.commit()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        latest = (
            db.query(DatasetVersion).filter_by(status="imported")
            .order_by(DatasetVersion.id.desc()).first()
        )
    except SQLAlchemyError as exc:
        logger.error("Database health check failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={
            "status": "unhealthy", "database": "unhealthy", "version": app.version,
            "environment": settings.environment,
        })
    return {
        "status": "healthy", "database": "healthy", "database_backend": settings.database_backend,
        "ai": ai.status(), "version": app.version, "environment": settings.environment,
        "onet_version": latest.name.removeprefix("O*NET ") if latest else None,
        "jwt_secret_configured": SECRET_CONFIGURED,
    }


@app.post("/auth/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    email = request.email.lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    if not request.name.strip():
        raise HTTPException(status_code=422, detail="Enter a display name.")
    user = User(
        email=email,
        name=request.name.strip(),
        password_hash=hash_password(request.password),
        role="student",
    )
    user.profile = Profile()
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from None
    return TokenResponse(
        access_token=create_token(user.id, user.session_version),
        role=user.role,
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=request.email.lower()).first()
    verified = verify_password(request.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if not user or not verified:
        logger.info("Login rejected for client %s: invalid credentials",
                    http_request.client.host if http_request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(
        access_token=create_token(user.id, user.session_version),
        role=user.role,
    )


@app.get("/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role,
            "created_at": user.created_at}


@app.post("/auth/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(update(User).where(User.id == user.id).values(session_version=User.session_version + 1))
    db.commit()
    return {"signed_out": True}


@app.post("/auth/recovery-code")
def create_recovery_code(request: PasswordConfirmation, user: User = Depends(current_user),
                         db: Session = Depends(get_db)):
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(403, "Current password is incorrect.")
    recovery_code = token_urlsafe(32)
    user.recovery_hash = recovery_digest(recovery_code)
    db.commit()
    return JSONResponse({"recovery_code": recovery_code}, headers={"Cache-Control": "no-store"})


@app.post("/auth/reset-password")
def reset_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=request.email.lower()).first()
    digest = recovery_digest(request.recovery_code)
    if not user or not user.recovery_hash or not compare_digest(digest, user.recovery_hash):
        raise HTTPException(400, "Email or recovery code is invalid.")
    result = db.execute(
        update(User).where(User.id == user.id, User.recovery_hash == digest).values(
            password_hash=hash_password(request.password), recovery_hash=None,
            session_version=User.session_version + 1,
        )
    )
    if result.rowcount != 1:
        raise HTTPException(400, "Email or recovery code is invalid.")
    db.commit()
    return {"password_reset": True}


@app.get("/profile")
def get_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        return {"id": None, "user_id": user.id}
    return profile


@app.put("/profile")
def update_profile(
    request: ProfileRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@app.get("/occupations/search")
def search_occupations(
    q: str = Query(default="", max_length=255),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query_text = q.strip()
    if not query_text:
        return []
    match = "%" + query_text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    query = (
        db.query(Occupation)
        .join(AlternateTitle, isouter=True)
        .filter(
            Occupation.dataset_version.is_not(None),
            or_(
                Occupation.title.ilike(match, escape="\\"),
                Occupation.description.ilike(match, escape="\\"),
                Occupation.onet_soc_code.ilike(match, escape="\\"),
                AlternateTitle.title.ilike(match, escape="\\"),
            )
        )
        .distinct()
        .order_by(Occupation.title, Occupation.id)
        .limit(limit)
    )
    return [
        {
            "id": item.id,
            "onet_soc_code": item.onet_soc_code,
            "title": item.title,
            "description": item.description,
            "dataset_version": item.dataset_version,
        }
        for item in query.all()
    ]


@app.get("/occupations/saved")
def saved_careers(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Occupation).join(SavedCareer).where(SavedCareer.user_id == user.id)
                      .order_by(Occupation.title)).all()


@app.put("/occupations/saved/{occupation_id}")
def save_career(occupation_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    occupation = db.get(Occupation, occupation_id)
    if not occupation or occupation.dataset_version is None:
        raise HTTPException(404, "Occupation not found in the current import.")
    if not db.get(SavedCareer, (user.id, occupation_id)):
        db.add(SavedCareer(user_id=user.id, occupation_id=occupation_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if not db.get(SavedCareer, (user.id, occupation_id)):
                raise
    return {"saved": True}


@app.delete("/occupations/saved/{occupation_id}")
def remove_saved_career(occupation_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(SavedCareer).where(SavedCareer.user_id == user.id, SavedCareer.occupation_id == occupation_id))
    db.commit()
    return {"saved": False}


@app.get("/occupations/{occupation_id}")
def occupation_detail(
    occupation_id: int,
    category: str | None = Query(default=None, max_length=64),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=300, ge=1, le=500),
    db: Session = Depends(get_db),
):
    occupation = db.get(Occupation, occupation_id)
    if not occupation or occupation.dataset_version is None:
        raise HTTPException(status_code=404, detail="Occupation not found")
    descriptor_query = db.query(Descriptor).filter_by(occupation_id=occupation_id)
    categories = [row[0] for row in descriptor_query.with_entities(Descriptor.category)
                  .distinct().order_by(Descriptor.category)]
    if category:
        descriptor_query = descriptor_query.filter_by(category=category)
    descriptors = descriptor_query.order_by(Descriptor.category, Descriptor.name, Descriptor.id).offset(offset).limit(limit).all()
    titles = db.query(AlternateTitle).filter_by(occupation_id=occupation_id).all()
    related = db.query(RelatedOccupation).filter_by(occupation_id=occupation_id).all()
    return {
        "attribution": {"credit": ONET_CREDIT, "source_url": ONET_URL, "license_url": ONET_LICENSE,
                        "notice": "Imported and reformatted by SkillBridge AI; not endorsed by USDOL/ETA."},
        "descriptor_count": descriptor_query.count(),
        "categories": categories,
        "occupation": {
            "id": occupation.id,
            "onet_soc_code": occupation.onet_soc_code,
            "title": occupation.title,
            "description": occupation.description,
            "dataset_version": occupation.dataset_version,
        },
        "alternate_titles": [item.title for item in titles],
        "related_occupations": [
            {
                "onet_soc_code": item.related_onet_soc_code,
                "title": item.related_title,
            }
            for item in related
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


@app.post("/occupations/compare")
def compare_careers(
    request: CareerCompareRequest,
    db: Session = Depends(get_db),
):
    unique_ids = list(dict.fromkeys(request.occupation_ids))
    if len(unique_ids) < 2:
        raise HTTPException(422, "Select at least two different occupations.")
    occupations = [
        db.get(Occupation, occupation_id)
        for occupation_id in unique_ids
    ]
    occupations = [occupation for occupation in occupations if occupation is not None and occupation.dataset_version]
    if len(occupations) != len(unique_ids):
        raise HTTPException(status_code=404, detail="One or more occupations were not found")
    result = []
    for occupation in occupations:
        descriptors = (
            db.query(Descriptor)
            .filter(
                Descriptor.occupation_id == occupation.id,
                Descriptor.category.in_(RATED_SKILL_CATEGORIES), Descriptor.scale == "IM",
                Descriptor.rating.is_not(None),
            )
            .order_by(Descriptor.rating.desc(), Descriptor.name).limit(50).all()
        )
        descriptors = [d for d in descriptors if
                       d.attributes.get("Recommend Suppress") != "Y" and d.attributes.get("Not Relevant") != "Y"]
        result.append(
            {
                "id": occupation.id,
                "onet_soc_code": occupation.onet_soc_code,
                "title": occupation.title,
                "description": occupation.description,
                "dataset_version": occupation.dataset_version,
                "top_descriptors": [
                    {
                        "category": descriptor.category,
                        "name": descriptor.name,
                        "rating": descriptor.rating,
                        "scale": descriptor.scale,
                    }
                    for descriptor in descriptors[:20]
                ],
            }
        )
    return {"source": "Official O*NET descriptors", "occupations": result}


@app.post("/custom-occupations")
def create_custom_occupation(
    request: CustomOccupationRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = CustomOccupation(
        user_id=user.id,
        title=request.title.strip(),
        industry=request.industry.strip() if request.industry else None,
        description=request.description.strip() if request.description else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/custom-occupations")
def list_custom_occupations(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(CustomOccupation)
        .filter_by(user_id=user.id)
        .order_by(CustomOccupation.created_at.desc())
        .all()
    )


@app.delete("/custom-occupations/{occupation_id}")
def delete_custom_occupation(
    occupation_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = db.query(CustomOccupation).filter_by(
        id=occupation_id,
        user_id=user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Custom occupation not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@app.post("/admin/onet/import")
def onet_import(
    file: UploadFile = File(...),
    version: str = Query(default="user-supplied", max_length=32, pattern=r"^[\w .-]+$"),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="O*NET archive must be a ZIP file")
    if file.size is None or file.size > MAX_ONET_UPLOAD:
        raise HTTPException(status_code=413, detail="O*NET archive exceeds 500 MB")
    if not _onet_import_lock.acquire(blocking=False):
        raise HTTPException(409, "An import is already in progress.")
    try:
        result = import_onet_zip(db, file.file, version.strip())
        register_import(db, result)
        db.commit()
    except OnetImportError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from None
    finally:
        _onet_import_lock.release()
        file.file.close()
    return {
        "import_status": "completed",
        "archive": Path(file.filename).name,
        **result,
    }


@app.post("/ai/generate")
def ai_generate(
    request: AIGenerateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    started = monotonic()
    records = retrieval.search(db, request.question)
    prompt = (
        f"Purpose: {request.purpose}\n"
        f"Question: {request.question}\n\n"
        "Provide educational career guidance. Do not guarantee admission or employment.\n\n"
        f"{source_context(records)}"
    )
    try:
        answer = ai.generate(prompt)
    except AIProviderError as exc:
        record_ai_usage(db, user, "career_guidance", False, started)
        raise HTTPException(status_code=503, detail=str(exc))
    record_ai_usage(db, user, "career_guidance", True, started)
    return {
        "answer": answer,
        "sources": records,
        "generated": True,
        "retrieved": bool(records),
        "provider": ai.active,
    }


@app.post("/skill-gap")
def skill_gap(
    request: SkillGapRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    occupation = None
    if request.occupation_id:
        occupation = db.get(Occupation, request.occupation_id)
    elif request.occupation_title:
        occupation = (
            db.query(Occupation)
            .filter(Occupation.dataset_version.is_not(None),
                or_(
                    Occupation.title.ilike(request.occupation_title.replace("%", r"\%").replace("_", r"\_"), escape="\\"),
                    Occupation.onet_soc_code == request.occupation_title,
                )
            )
            .first()
        )
    if request.occupation_id and (not occupation or not occupation.dataset_version):
        raise HTTPException(status_code=404, detail="Occupation not found")

    if not occupation:
        custom = (
            db.query(CustomOccupation)
            .filter_by(user_id=user.id, title=request.occupation_title)
            .first()
            if request.occupation_title
            else None
        )
        return {
            "occupation": custom.title if custom else request.occupation_title,
            "strengths": [],
            "gaps": [],
            "source": "Not verified against O*NET",
            "notice": (
                "This occupation is not represented by imported official O*NET data. "
                "Use AI guidance only as general, unverified career information."
            ),
        }

    current = {
        str(skill).strip().lower()
        for skill in request.current_skills
        if str(skill).strip()
    }
    required = (
        db.query(Descriptor)
        .filter(
            Descriptor.occupation_id == occupation.id,
            Descriptor.category.in_(RATED_SKILL_CATEGORIES),
        )
        .order_by(Descriptor.category, Descriptor.name, Descriptor.id)
        .all()
    )
    unique = {}
    for descriptor in required:
        if (descriptor.attributes.get("Recommend Suppress") == "Y"
                or descriptor.attributes.get("Not Relevant") == "Y"):
            continue
        key = descriptor.name.casefold()
        if key not in unique or descriptor.scale == "IM":
            unique[key] = descriptor
    gaps = []
    strengths = []
    for descriptor in unique.values():
        matched = descriptor.name.casefold() in current
        item = {
            "name": descriptor.name,
            "rating": descriptor.rating,
            "scale": descriptor.scale,
            "category": descriptor.category,
        }
        if matched:
            strengths.append(item)
        else:
            gaps.append(item)
    return {
        "occupation": occupation.title,
        "strengths": strengths,
        "gaps": gaps,
        "notice": "Matches are self-reported. A gap means a descriptor was not reported, not that ability was tested.",
        "source": (
            "Official O*NET descriptors"
            if unique
            else "No imported O*NET descriptors"
        ),
    }


@app.post("/roadmaps")
def create_roadmap(
    request: RoadmapRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    started = monotonic()
    records = retrieval.search(db, request.occupation_title)
    prompt = (
        f"Create an adaptive learning roadmap for {request.occupation_title}. "
        f"User interests: {request.interests or 'Not provided'}. "
        f"Current skills: {request.current_skills}. "
        "Include prerequisites, measurable objectives, time ranges, practice projects, and completion criteria. "
        "Consider college, vocational, apprenticeship and work-based paths where appropriate.\n"
        f"{source_context(records)}"
    )
    try:
        content = ai.generate(prompt)
    except AIProviderError as exc:
        record_ai_usage(db, user, "roadmap", False, started)
        raise HTTPException(status_code=503, detail=str(exc))
    roadmap = Roadmap(
        user_id=user.id,
        occupation_title=request.occupation_title.strip(),
        content=content,
        sources=records,
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    record_ai_usage(db, user, "roadmap", True, started)
    return {
        "id": roadmap.id,
        "occupation_title": roadmap.occupation_title,
        "content": content,
        "sources": records,
    }


@app.get("/roadmaps")
def list_roadmaps(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Roadmap)
        .filter_by(user_id=user.id)
        .order_by(Roadmap.created_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "occupation_title": item.occupation_title,
            "content": item.content,
            "sources": item.sources,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


@app.delete("/roadmaps/{roadmap_id}")
def delete_roadmap(
    roadmap_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Roadmap).filter_by(id=roadmap_id, user_id=user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    db.execute(update(LearningActivity).where(
        LearningActivity.roadmap_id == roadmap_id, LearningActivity.user_id == user.id,
    ).values(roadmap_id=None))
    db.delete(item)
    db.commit()
    return {"deleted": True}


@app.post("/portfolio/upload")
def upload_portfolio(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    content = file.file.read(MAX_PORTFOLIO_UPLOAD + 1)
    if len(content) > MAX_PORTFOLIO_UPLOAD:
        raise HTTPException(status_code=413, detail="Portfolio image exceeds 10 MB")
    try:
        with Image.open(io.BytesIO(content), formats=["PNG", "JPEG", "WEBP", "GIF"]) as image:
            if image.width * image.height > 20_000_000:
                raise HTTPException(413, "Portfolio images must be at most 20 megapixels.")
            image = ImageOps.exif_transpose(image)
            image.thumbnail((1800, 1800))
            picture = image.convert("RGBA")
            rgb = Image.new("RGB", picture.size, "white")
            rgb.paste(picture, mask=picture.getchannel("A"))
            sanitized = io.BytesIO()
            rgb.save(sanitized, format="PNG")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise HTTPException(400, "Upload a valid PNG, JPEG, WEBP, or GIF image.") from None
    UPLOAD_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.png"
    target = UPLOAD_DIR / stored_name
    target.write_bytes(sanitized.getvalue())
    item = Portfolio(
        user_id=user.id,
        filename=Path((file.filename or "portfolio").replace("\\", "/")).name[:255],
        stored_path=stored_name,
        mime_type="image/png",
    )
    db.add(item)
    try:
        db.commit()
    except SQLAlchemyError:
        target.unlink(missing_ok=True)
        raise
    db.refresh(item)
    return {"id": item.id, "filename": item.filename}


@app.get("/portfolio")
def list_portfolios(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Portfolio)
        .filter_by(user_id=user.id)
        .order_by(Portfolio.created_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "evaluation": item.evaluation,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


@app.post("/portfolio/{portfolio_id}/evaluate")
def evaluate_portfolio(
    portfolio_id: int,
    request: PortfolioReviewRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Portfolio).filter_by(id=portfolio_id, user_id=user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    try:
        image_bytes = (UPLOAD_DIR / Path(item.stored_path).name).read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Stored portfolio image is unavailable")
    prompt = (
        "Review this student portfolio image for clarity, visual hierarchy, accessibility, "
        "project readability, and presentation. Clearly distinguish what is visible in the "
        "image from inferences. Provide constructive, specific educational feedback."
    )
    started = monotonic()
    try:
        evaluation = ai.generate_with_image(prompt, image_bytes, item.mime_type)
    except AIProviderError as exc:
        record_ai_usage(db, user, "portfolio_review", False, started)
        raise HTTPException(status_code=503, detail=str(exc))
    item.evaluation = evaluation
    db.commit()
    record_ai_usage(db, user, "portfolio_review", True, started)
    return {"id": item.id, "evaluation": evaluation}


@app.post("/projects")
def create_project(
    request: ProjectRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    started = monotonic()
    title = request.title.strip() if request.title else f"{request.occupation.strip()} portfolio project"
    records = retrieval.search(db, request.occupation)
    prompt = (
        f"Generate a realistic, ethical project for a student pursuing {request.occupation.strip()}. "
        f"Project theme: {title}. Student-provided experience and skills: {request.experience or 'Not provided'}. "
        "Include difficulty, materials, objectives, phases, outcomes and portfolio presentation. "
        "Label this as AI-generated guidance.\n"
        f"{source_context(records)}"
    )
    try:
        description = ai.generate(prompt)
    except AIProviderError as exc:
        record_ai_usage(db, user, "project_generator", False, started)
        raise HTTPException(status_code=503, detail=str(exc))
    project = Project(
        user_id=user.id,
        title=title[:255],
        description=description,
        status="planned",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    record_ai_usage(db, user, "project_generator", True, started)
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "status": project.status,
        "sources": records,
    }


@app.get("/projects")
def list_projects(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Project)
        .filter_by(user_id=user.id)
        .order_by(Project.created_at.desc())
        .all()
    )


@app.patch("/projects/{project_id}")
def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if request.status not in {"planned", "in_progress", "completed"}:
        raise HTTPException(status_code=400, detail="Invalid project status")
    project = db.query(Project).filter_by(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = request.status
    db.commit()
    db.refresh(project)
    return project


@app.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}


@app.get("/opportunities")
def opportunities(q: str = Query(default="", max_length=160)):
    query_text = q.strip()
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


@app.post("/opportunities/save")
def save_opportunity(
    request: OpportunitySaveRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = Opportunity(
        user_id=user.id,
        title=request.title,
        organization=request.organization,
        url=str(request.url) if request.url else None,
        details=request.details,
        saved=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/opportunities/saved")
def list_saved_opportunities(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Opportunity)
        .filter_by(user_id=user.id, saved=True)
        .order_by(Opportunity.id.desc())
        .all()
    )


@app.delete("/opportunities/saved/{opportunity_id}")
def remove_saved_opportunity(
    opportunity_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Opportunity).filter_by(id=opportunity_id, user_id=user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Saved opportunity not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@app.patch("/opportunities/saved/{opportunity_id}")
def update_opportunity(opportunity_id: int, request: OpportunityStatusRequest,
                       user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.query(Opportunity).filter_by(id=opportunity_id, user_id=user.id).first()
    if not item:
        raise HTTPException(404, "Saved opportunity not found.")
    item.application_status = request.application_status
    db.commit()
    db.refresh(item)
    return item


@app.post("/assessments")
def save_assessment(
    request: SkillAssessmentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = SkillAssessment(
        user_id=user.id,
        occupation_title=request.occupation_title,
        skill_name=request.skill_name,
        rating=request.rating,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/assessments")
def list_assessments(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(SkillAssessment)
        .filter_by(user_id=user.id)
        .order_by(SkillAssessment.created_at.desc())
        .all()
    )


@app.post("/activities")
def create_activity(
    request: LearningActivityRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if request.roadmap_id:
        roadmap = db.query(Roadmap).filter_by(id=request.roadmap_id, user_id=user.id).first()
        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")
    item = LearningActivity(
        user_id=user.id,
        roadmap_id=request.roadmap_id,
        title=request.title,
        status=request.status,
        notes=request.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/activities")
def list_activities(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(LearningActivity)
        .filter_by(user_id=user.id)
        .order_by(LearningActivity.created_at.desc())
        .all()
    )


@app.patch("/activities/{activity_id}")
def update_activity(
    activity_id: int,
    request: LearningActivityRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = db.query(LearningActivity).filter_by(id=activity_id, user_id=user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Learning activity not found")
    if "roadmap_id" in request.model_fields_set:
        if request.roadmap_id and not db.query(Roadmap).filter_by(id=request.roadmap_id, user_id=user.id).first():
            raise HTTPException(404, "Roadmap not found")
        item.roadmap_id = request.roadmap_id
    item.title = request.title
    item.status = request.status
    item.notes = request.notes
    db.commit()
    db.refresh(item)
    return item


@app.get("/progress")
def progress_summary(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    roadmaps = db.query(Roadmap).filter_by(user_id=user.id).count()
    projects = db.query(Project).filter_by(user_id=user.id).all()
    activities = db.query(LearningActivity).filter_by(user_id=user.id).all()
    assessments = db.query(SkillAssessment).filter_by(user_id=user.id).all()
    opportunities = db.query(Opportunity).filter_by(user_id=user.id, saved=True).count()
    return {
        "saved_roadmaps": roadmaps,
        "project_total": len(projects),
        "projects_planned": sum(project.status == "planned" for project in projects),
        "projects_in_progress": sum(project.status == "in_progress" for project in projects),
        "projects_completed": sum(project.status == "completed" for project in projects),
        "learning_activity_total": len(activities),
        "learning_activities_completed": sum(
            activity.status == "completed" for activity in activities
        ),
        "skill_assessment_total": len(assessments),
        "saved_opportunities": opportunities,
        "portfolio_total": db.query(Portfolio).filter_by(user_id=user.id).count(),
    }


@app.get("/training-consent")
def get_training_consent(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    consent = db.query(TrainingConsent).filter_by(user_id=user.id).first()
    if not consent:
        return {
            "consent_enabled": False,
            "disclosure_version": "2026-11-21",
            "withdrawn_at": None,
        }
    return consent


@app.put("/training-consent")
def update_training_consent(
    request: TrainingConsentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_community_writes(db)
    consent = db.query(TrainingConsent).filter_by(user_id=user.id).first()
    if not consent:
        consent = TrainingConsent(user_id=user.id)
        db.add(consent)
    consent.consent_enabled = request.consent_enabled
    consent.disclosure_version = request.disclosure_version
    consent.updated_at = utcnow()
    consent.withdrawn_at = None if request.consent_enabled else utcnow()
    if not request.consent_enabled:
        remove_user_training_permission(db, user.id)
    db.commit()
    db.refresh(consent)
    return consent


def lock_community_writes(db: Session):
    # Serialize review, draft, and consent writes across database connections.
    db.execute(update(CommunityPolicy).where(CommunityPolicy.id == 1)
               .values(write_version=CommunityPolicy.write_version + 1))


def remove_user_training_permission(db: Session, user_id: int):
    items = select(CommunityContribution.id).where(CommunityContribution.user_id == user_id)
    invalidate_datasets(db, items)
    db.execute(update(CommunityContribution).where(CommunityContribution.user_id == user_id)
               .values(consent_to_training=False))


@app.post("/auth/delete-account")
def delete_account(request: PasswordConfirmation, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(409, "Administrator accounts require operator-managed deletion.")
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(403, "Current password is incorrect.")
    lock_community_writes(db)
    items = select(CommunityContribution.id).where(CommunityContribution.user_id == user.id)
    invalidate_datasets(db, items)
    db.execute(delete(ApprovedKnowledge).where(ApprovedKnowledge.source_contribution_id.in_(items)))
    db.execute(delete(ReviewHistory).where(ReviewHistory.contribution_id.in_(items)))
    files = db.scalars(select(Portfolio.stored_path).where(Portfolio.user_id == user.id)).all()
    for table in (CommunityContribution, TrainingConsent, AIUsage, SkillAssessment,
                  LearningActivity, Roadmap, Project, Portfolio, Opportunity, CustomOccupation, SavedCareer):
        db.execute(delete(table).where(table.user_id == user.id))
    db.delete(user)
    db.commit()
    failures = 0
    for filename in files:
        try:
            (UPLOAD_DIR / Path(filename).name).unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove a private portfolio file after account deletion.")
            failures += 1
    return {"deleted": True, "file_cleanup_pending": failures}


@app.post("/contributions")
def submit_contribution(
    request: ContributionRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_community_writes(db)
    consent = db.query(TrainingConsent).filter_by(user_id=user.id).first()
    if not request.copyright_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Copyright confirmation is required for community contributions",
        )
    if request.consent_to_training and (
        consent is None or not consent.consent_enabled or consent.disclosure_version != CONSENT_VERSION
    ):
        raise HTTPException(
            status_code=400,
            detail="Enable training permission in Settings before consenting to training",
        )
    if any(sanitize_for_training(value) != value for value in (request.title, request.body, request.source or "")):
        raise HTTPException(422, "Remove personal identifiers before submitting this contribution.")
    item = CommunityContribution(
        user_id=user.id,
        title=request.title.strip(),
        body=request.body.strip(),
        category=request.category.strip().lower(),
        source=request.source.strip() if request.source else None,
        consent_to_training=request.consent_to_training,
        copyright_confirmed=request.copyright_confirmed,
        deidentified=False,
        review_status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ContributionResponse(
        id=item.id,
        title=item.title,
        category=item.category,
        review_status=item.review_status,
        consent_to_training=item.consent_to_training,
        quality_rating=item.quality_rating,
    )


@app.get("/contributions")
def my_contributions(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(CommunityContribution)
        .filter_by(user_id=user.id)
        .order_by(CommunityContribution.submitted_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "title": item.title,
            "category": item.category,
            "review_status": item.review_status,
            "quality_rating": item.quality_rating,
            "consent_to_training": item.consent_to_training,
            "submitted_at": item.submitted_at.isoformat(),
        }
        for item in items
    ]


@app.put("/contributions/{contribution_id}/consent")
def set_contribution_consent(contribution_id: int, request: TrainingConsentRequest,
                             user: User = Depends(current_user), db: Session = Depends(get_db)):
    lock_community_writes(db)
    item = db.query(CommunityContribution).filter_by(id=contribution_id, user_id=user.id).first()
    if not item:
        raise HTTPException(404, "Contribution not found.")
    if request.consent_enabled:
        global_consent = db.query(TrainingConsent).filter_by(user_id=user.id, consent_enabled=True,
                                                             disclosure_version=CONSENT_VERSION).first()
        if not global_consent or not item.copyright_confirmed:
            raise HTTPException(400, "Enable training permission in Settings and confirm ownership first.")
    else:
        invalidate_datasets(db, [item.id])
    item.consent_to_training = request.consent_enabled
    db.commit()
    return {"id": item.id, "consent_to_training": item.consent_to_training}


@app.get("/admin/contributions")
def admin_contributions(
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(CommunityContribution)
        .order_by(CommunityContribution.submitted_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "category": item.category,
            "source": item.source,
            "review_status": item.review_status,
            "quality_rating": item.quality_rating,
            "consent_to_training": item.consent_to_training,
            "deidentified": item.deidentified,
            "copyright_confirmed": item.copyright_confirmed,
            "submitted_at": item.submitted_at.isoformat(),
        }
        for item in items
    ]


@app.post("/admin/contributions/{contribution_id}/review")
def review_contribution(
    contribution_id: int,
    request: ContributionReviewRequest,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    lock_community_writes(db)
    item = db.get(CommunityContribution, contribution_id)
    if not item:
        raise HTTPException(status_code=404, detail="Contribution not found")
    existing = db.query(ApprovedKnowledge).filter_by(
        source_contribution_id=item.id
    ).first()
    if request.status == "approved":
        if not request.deidentified:
            raise HTTPException(
                status_code=400,
                detail="Approved contributions must be confirmed as de-identified",
            )
        if not item.copyright_confirmed:
            raise HTTPException(
                status_code=400,
                detail="Approved contributions require copyright confirmation",
            )
        quality = request.quality_rating
        if quality is None or quality < 3:
            raise HTTPException(
                status_code=400,
                detail="Approved contributions require a quality rating of at least 3",
            )
        public_title = request.public_title or item.title
        public_body = request.public_body or item.body
        public_source = request.public_source if request.public_source is not None else item.source
        if any(sanitize_for_training(value) != value for value in (public_title, public_body, public_source or "")):
            raise HTTPException(422, "Remove personal identifiers from the public copy before approval.")
        embedding = hashed_embedding(public_title + " " + public_body)
        if existing:
            existing.title = public_title
            existing.body = public_body
            existing.category = item.category
            existing.source_reference = public_source
            existing.quality_score = quality
            existing.embedding_json = json.dumps(embedding)
        else:
            db.add(
                ApprovedKnowledge(
                    source_contribution_id=item.id,
                    title=public_title,
                    body=public_body,
                    category=item.category,
                    source_reference=public_source,
                    quality_score=quality,
                    embedding_json=json.dumps(embedding),
                )
            )
    elif existing:
        db.delete(existing)
    invalidate_datasets(db, [item.id])
    item.review_status = request.status
    item.deidentified = request.deidentified
    item.quality_rating = request.quality_rating
    db.add(
        ReviewHistory(
            contribution_id=item.id,
            reviewer_id=admin.id,
            status=request.status,
            quality_rating=request.quality_rating,
            notes=request.notes,
        )
    )
    db.commit()
    return {
        "id": item.id,
        "review_status": item.review_status,
        "quality_rating": item.quality_rating,
    }


@app.get("/admin/contributions/{contribution_id}/history")
def contribution_history(
    contribution_id: int,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(ReviewHistory)
        .filter_by(contribution_id=contribution_id)
        .order_by(ReviewHistory.created_at.desc())
        .all()
    )


@app.post("/admin/datasets/build")
def build_dataset(
    request: DatasetBuildRequest,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    lock_community_writes(db)
    if request.name.upper().startswith("O*NET "):
        raise HTTPException(400, "The O*NET dataset prefix is reserved for reference imports.")
    existing = db.query(DatasetVersion).filter_by(name=request.name.strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Dataset version name already exists")
    snapshot = build_reviewed_dataset(db, request.name.strip())
    dataset = DatasetVersion(
        name=request.name.strip(),
        status="draft",
        train_count=snapshot["train_count"],
        validation_count=snapshot["validation_count"],
    )
    db.add(dataset)
    db.flush()
    for record in snapshot["records"]:
        db.add(
            DatasetRecord(
                dataset_version_id=dataset.id,
                contribution_id=record["contribution_id"],
                content_hash=record["content_hash"],
                title=record["title"],
                text=record["text"],
                category=record["category"],
                source_reference=record["source_reference"],
                quality_rating=record["quality_rating"],
                split=record["split"],
            )
        )
    db.add(
        TrainingHistory(
            dataset_version_id=dataset.id,
            action="dataset_snapshot",
            status="draft",
            details=json.dumps(
                {
                    "eligible_before_dedup": snapshot["eligible_before_dedup"],
                    "train_count": snapshot["train_count"],
                    "validation_count": snapshot["validation_count"],
                    "training_performed": False,
                }
            ),
        )
    )
    db.commit()
    return {
        "id": dataset.id,
        "name": dataset.name,
        "status": dataset.status,
        "eligible_before_dedup": snapshot["eligible_before_dedup"],
        "train_count": snapshot["train_count"],
        "validation_count": snapshot["validation_count"],
        "training_performed": False,
    }


@app.get("/admin/datasets")
def list_datasets(
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return db.query(DatasetVersion).order_by(DatasetVersion.created_at.desc()).all()


@app.get("/admin/datasets/{dataset_id}/records")
def list_dataset_records(
    dataset_id: int,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetVersion, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    if dataset.status != "draft":
        raise HTTPException(409, "This dataset is not an eligible training draft.")
    records = (
        db.query(DatasetRecord)
        .filter_by(dataset_version_id=dataset_id)
        .order_by(DatasetRecord.split, DatasetRecord.content_hash)
        .all()
    )
    return {
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "status": dataset.status,
            "train_count": dataset.train_count,
            "validation_count": dataset.validation_count,
        },
        "records": [
            {
                "content_hash": record.content_hash,
                "title": record.title,
                "category": record.category,
                "quality_rating": record.quality_rating,
                "split": record.split,
            }
            for record in records
        ],
    }


@app.get("/admin/training/history")
def training_history(
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(TrainingHistory)
        .order_by(TrainingHistory.created_at.desc())
        .all()
    )


@app.get("/admin/models")
def list_models(
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()


@app.post("/admin/models")
def register_model(
    payload: ModelVersionRequest,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    name = payload.name
    if payload.status == "evaluated" and not payload.evaluation_summary:
        raise HTTPException(422, "Record evaluation results before marking a model evaluated.")
    existing = db.query(ModelVersion).filter_by(name=name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Model version name already exists")
    item = ModelVersion(
        name=name,
        provider=payload.provider,
        status=payload.status,
        evaluation_summary=payload.evaluation_summary,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/admin/dashboard")
def admin_dashboard(
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    contributions = db.query(CommunityContribution).all()
    consents = db.query(TrainingConsent).all()
    consented = sum(consent.consent_enabled for consent in consents)
    eligible = build_reviewed_dataset(db, "count")["eligible_before_dedup"]
    usage = db.query(AIUsage).all()
    return {
        "total_contributions": len(contributions),
        "pending": sum(
            contribution.review_status == "pending"
            for contribution in contributions
        ),
        "approved": sum(
            contribution.review_status == "approved"
            for contribution in contributions
        ),
        "rejected": sum(
            contribution.review_status == "rejected"
            for contribution in contributions
        ),
        "training_consent_users": consented,
        "training_consent_records": sum(
            contribution.consent_to_training
            for contribution in contributions
        ),
        "training_eligible_records": eligible,
        "approved_knowledge_records": db.query(ApprovedKnowledge).count(),
        "dataset_versions": db.query(DatasetVersion).count(),
        "dataset_records": db.query(DatasetRecord).count(),
        "training_history_entries": db.query(TrainingHistory).count(),
        "model_versions": db.query(ModelVersion).count(),
        "ai_requests": len(usage),
        "ai_requests_successful": sum(item.success for item in usage),
    }
