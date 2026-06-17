from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def validation_error_handler(
    _request: object,
    _exception: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        status_code=400,
        error="bad_request",
        message="Invalid request",
    )


def _session_not_found_response() -> JSONResponse:
    return _error_response(
        status_code=404,
        error="not_found",
        message="Session not found",
    )


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
        },
    )
