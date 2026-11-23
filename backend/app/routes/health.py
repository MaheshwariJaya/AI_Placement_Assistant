from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.core.database import check_database_connection
from app.config import get_settings

router = APIRouter(prefix="/health", tags=["System Health"])
settings = get_settings()


@router.get(
    "/live",
    summary="Liveness Probe",
    description="Returns 200 OK if the ASGI process is active and accepting requests.",
)
async def liveness_probe():
    """Lightweight probe verifying the application process is running."""
    return {
        "success": True,
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@router.get(
    "/ready",
    summary="Readiness Probe",
    description="Tests connectivity to the PostgreSQL database and reports operational readiness.",
)
async def readiness_probe(response: Response):
    """Readiness probe verifying database connectivity."""
    db_status = await check_database_connection()

    if db_status["connected"]:
        return {
            "success": True,
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": {
                "status": "connected",
                "host": db_status["host"],
                "database_name": db_status["database"],
                "schema": settings.DB_SCHEMA,
                "latency_ms": db_status["latency_ms"],
            },
            "ai_engine": {
                "active_provider": settings.AI_PROVIDER,
                "gemini_model": settings.GEMINI_MODEL,
                "openai_model": settings.OPENAI_MODEL,
            },
        }

    # If database is not reachable, mark response as Service Unavailable (503)
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "success": False,
        "status": "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "status": "disconnected",
            "host": db_status["host"],
            "database_name": db_status["database"],
            "latency_ms": db_status["latency_ms"],
            "error": db_status["error"],
            "remedy": "Ensure PostgreSQL service is running on 127.0.0.1:5432 and database 'placement_db' exists.",
        },
        "ai_engine": {
            "active_provider": settings.AI_PROVIDER,
        },
    }

