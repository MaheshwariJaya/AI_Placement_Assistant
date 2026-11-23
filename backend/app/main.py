from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.errors import register_error_handlers
from app.core.seed import ensure_system_reference_metadata
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.organizations import router as org_router
from app.routes.users import router as user_router
from app.routes.resumes import router as resume_router
from app.routes.companies import router as company_router
from app.routes.jobs import router as job_router
from app.routes.intelligence import router as intelligence_router
from app.routes.placement import router as placement_router
from app.routes.career_assistant import router as career_assistant_router
from app.routes.resume_feedback import router as resume_feedback_router
from app.routes.mock_interviews import router as mock_interviews_router
from app.routes.readiness import router as readiness_router
from app.routes.arena import router as arena_router
from app.routes.tpo_intelligence import router as tpo_intelligence_router
from app.routes.drive_management import router as drive_management_router
from app.routes.reports import router as reports_router
from app.routes.candidate_evaluation import router as candidate_evaluation_router
from app.routes.candidate_comparison import router as candidate_comparison_router
from app.routes.audit import router as audit_router

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("placement_system")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown routines."""
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' mode...")
    logger.info(f"AI Provider configured as: '{settings.AI_PROVIDER}'")
    await ensure_system_reference_metadata()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-Powered Placement Intelligence System REST API. "
            "Modular monolithic architecture integrating resume intelligence, "
            "deterministic eligibility verification, weighted compatibility scoring, "
            "and AI career coaching."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Centralized Error Handlers
    register_error_handlers(app)

    # Mount Core & Health Routes
    app.include_router(health_router)
    app.include_router(health_router, prefix=settings.API_V1_PREFIX)

    # Mount Phase 2 Authentication, Organization & User Routes
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(org_router, prefix=settings.API_V1_PREFIX)
    app.include_router(user_router, prefix=settings.API_V1_PREFIX)

    # Mount Phase 3 Resume Intelligence Routes
    app.include_router(resume_router, prefix=settings.API_V1_PREFIX)

    # Mount Phase 4 Company and Job Management Routes
    app.include_router(company_router, prefix=settings.API_V1_PREFIX)
    app.include_router(job_router, prefix=settings.API_V1_PREFIX)

    # Mount Phase 5 Placement Intelligence Routes
    app.include_router(intelligence_router, prefix=settings.API_V1_PREFIX)

    # Mount Phase 6 Placement & Recruitment Management Routes (+ Complete Drive Workspace)
    app.include_router(drive_management_router, prefix=settings.API_V1_PREFIX)
    app.include_router(placement_router, prefix=settings.API_V1_PREFIX)

    # Mount Phase 7 AI Career Assistant & Resume Feedback Routes
    app.include_router(career_assistant_router, prefix=settings.API_V1_PREFIX)
    app.include_router(career_assistant_router, prefix=f"{settings.API_V1_PREFIX}/intelligence")
    app.include_router(resume_feedback_router, prefix=settings.API_V1_PREFIX)
    app.include_router(mock_interviews_router, prefix=settings.API_V1_PREFIX)
    app.include_router(readiness_router, prefix=settings.API_V1_PREFIX)
    app.include_router(arena_router, prefix=settings.API_V1_PREFIX)
    app.include_router(tpo_intelligence_router, prefix=settings.API_V1_PREFIX)
    app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
    app.include_router(candidate_evaluation_router, prefix=settings.API_V1_PREFIX)
    app.include_router(candidate_comparison_router, prefix=settings.API_V1_PREFIX)
    app.include_router(audit_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"])
    async def root():
        """Root API welcome endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "health_live": "/health/live",
            "health_ready": "/health/ready",
            "api_v1_prefix": settings.API_V1_PREFIX,
        }

    return app


app = create_app()

