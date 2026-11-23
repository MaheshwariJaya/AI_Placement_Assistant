import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception for domain errors."""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class EntityNotFoundException(AppException):
    def __init__(
        self,
        entity_name_or_message: str,
        identifier: Optional[Any] = None,
        code: str = "ENTITY_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        if identifier is not None:
            msg = f"{entity_name_or_message} with identifier '{identifier}' was not found."
            d = {"entity": entity_name_or_message, "identifier": str(identifier)}
            if details:
                d.update(details)
        else:
            msg = entity_name_or_message
            d = details or {}
        super().__init__(
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            code=code,
            details=d,
        )


class ResourceConflictException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, code: str = "RESOURCE_CONFLICT"):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code=code,
            details=details,
        )


class AuthorizationException(AppException):
    def __init__(
        self,
        message: str = "You do not have permission to access this resource.",
        code: str = "FORBIDDEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code=code,
            details=details,
        )


# Backward and forward compatibility aliases
AppError = AppException
NotFoundError = EntityNotFoundException
PermissionDeniedError = AuthorizationException


def register_error_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers for standard JSON response formatting."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(f"Domain exception on {request.url.path}: {exc.code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info(f"Validation error on {request.url.path}: {exc.errors()}")
        formatted_errors = []
        for err in exc.errors():
            loc = " -> ".join([str(l) for l in err.get("loc", [])])
            formatted_errors.append({
                "field": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed. Please check the submitted fields.",
                    "details": {"validation_errors": formatted_errors},
                },
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled server exception on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please try again later.",
                    "details": {"error_type": exc.__class__.__name__},
                },
            },
        )

