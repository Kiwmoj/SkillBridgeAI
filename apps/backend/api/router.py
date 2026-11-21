"""Compose the versioned API router from the domain routers."""
from fastapi import APIRouter

from apps.backend.api.routes import (
    admin,
    analytics,
    auth,
    careers,
    community,
    guidance,
    health,
    opportunities,
    portfolio,
    profiles,
    projects,
    roadmaps,
    skills,
)

api_router = APIRouter()
for module in (health, auth, profiles, careers, guidance, skills, roadmaps, portfolio, projects,
               opportunities, analytics, community, admin):
    api_router.include_router(module.router)
