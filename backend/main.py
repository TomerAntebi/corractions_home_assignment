from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.routes.health_routes import health_router
from api.routes.session_routes import session_router
from core.error_responses import validation_error_handler


app = FastAPI()

app.add_exception_handler(RequestValidationError, validation_error_handler)
app.include_router(health_router)
app.include_router(session_router)
