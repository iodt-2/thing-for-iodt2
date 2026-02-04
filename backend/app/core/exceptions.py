"""
TwinScale-Lite Exceptions

Simplified exception handling for the TwinScale-Lite API.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
from fastapi.responses import JSONResponse
from fastapi import HTTPException, status, Request

logger = logging.getLogger(__name__)


class TwinScaleException(Exception):
    """Base exception for TwinScale-Lite"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class FusekiException(Exception):
    """Fuseki operations exception"""
    def __init__(
        self,
        message: str = "Fuseki operation failed",
        status_code: int = 500,
        detail: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.message} (Status: {self.status_code})"


class ValidationError(TwinScaleException):
    """Raised when validation fails"""
    def __init__(self, detail: str):
        self.status_code = status.HTTP_400_BAD_REQUEST
        self.detail = detail
        super().__init__(detail)


class NotFoundException(TwinScaleException):
    """Raised when a resource is not found"""
    def __init__(self, resource_type: str, resource_id: str):
        self.status_code = status.HTTP_404_NOT_FOUND
        self.detail = f"{resource_type} with id {resource_id} not found"
        super().__init__(self.detail)


async def fuseki_exception_handler(request: Request, exc: FusekiException):
    """Global Fuseki exception handler for FastAPI"""
    error_response = {
        "error": exc.message,
        "detail": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat(),
        "path": request.url.path
    }

    logger.error(
        f"Fuseki error occurred: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "detail": exc.detail
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )
