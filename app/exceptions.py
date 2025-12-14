import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):

    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        type_: str = "about:blank",
        instance: str | None = None,
    ):
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type_
        self.instance = instance


async def api_error_handler(request: Request, exc: ApiError):
    correlation_id = str(uuid.uuid4())
    logger.warning(f"[{correlation_id}] {exc.title}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status,
        content={
            "type": exc.type,
            "title": exc.title,
            "status": exc.status,
            "detail": exc.detail,
            "instance": exc.instance or str(request.url),
            "correlation_id": correlation_id,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    api_error = ApiError(
        status=exc.status_code,
        title="HTTP Error",
        detail=str(exc.detail),
        instance=str(request.url),
    )
    return await api_error_handler(request, api_error)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = str(uuid.uuid4())
    logger.warning(f"[{correlation_id}] Validation error: {exc.errors()}")

    api_error = ApiError(
        status=422,
        title="Validation Error",
        detail="Invalid input data",
        type_="https://example.com/validation-error",
        instance=str(request.url),
    )
    return await api_error_handler(request, api_error)


async def internal_error_handler(request: Request, exc: Exception):
    correlation_id = str(uuid.uuid4())
    logger.exception(f"[{correlation_id}] Internal server error: {exc}")

    api_error = ApiError(
        status=500,
        title="Internal Server Error",
        detail="Unexpected internal error",
        instance=str(request.url),
    )
    return await api_error_handler(request, api_error)


def setup_exception_handlers(app: FastAPI):
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, internal_error_handler)
