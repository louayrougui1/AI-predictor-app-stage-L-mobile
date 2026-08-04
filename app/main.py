import logging

import time
import http

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.auth.views import router as auth_router
from app.prediction.views import router as prediction_router
from app.core import lifespan
from app.core.config import get_settings
from app.probe.views import router as probe_router


app = FastAPI(
    title="AI predictor app",
    version="7.0.0",
    description="An AI predictor app that predicts the job duration",
    openapi_url="/openapi.json",
    docs_url="/",
    lifespan=lifespan.lifespan,
)


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(probe_router, prefix="/probe", tags=["probe"])
app.include_router(prediction_router, prefix="/predict", tags=["predict"])




request_logger = logging.getLogger("request_logger")
@app.middleware("http")
async def log_requests(request, call_next):

    start = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start

    client = request.client.host if request.client else "-"

    status_phrase = http.HTTPStatus(response.status_code).phrase

    request_logger.info(
        'FROM: %s : %s - "%s %s HTTP/%s" %s %s in %.3fs',
        __name__,
        client,
        request.method,
        request.url.path,
        request.scope["http_version"],
        response.status_code,
        status_phrase,
        duration,
    )
    return response
# Sets all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        str(origin).rstrip("/")
        for origin in get_settings().security.backend_cors_origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Guards against HTTP Host Header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_settings().security.allowed_hosts,
)
