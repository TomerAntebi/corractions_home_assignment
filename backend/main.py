from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.routes.health_routes import health_router
from api.routes.session_routes import session_router


app = FastAPI()

def validation_error_handler(
    _request: object,
    _exception: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": "bad_request",
            "message": "Invalid request",
        },
    )


app.add_exception_handler(RequestValidationError, validation_error_handler)
app.include_router(health_router)
app.include_router(session_router)
