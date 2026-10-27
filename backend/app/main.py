import json
import logging
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from app.api.routes import router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import RateLimiter
from app.services.seed import seed
from app.services.storage import cleanup
from app.core.body_limit import BodySizeLimit

settings = get_settings()
logger = logging.getLogger('scamshield')
logging.basicConfig(level=logging.INFO, format='%(message)s')
# Avoid Telegram HTTP request logs that could expose Bot API token URLs.
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
limiter = RateLimiter()


def same_origin(request: Request, origin: str) -> bool:
    """Accept the deployment's own origin without hardcoding preview domains."""
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    hosts = {request.headers.get('host', '').casefold()}
    # Vercel documents x-forwarded-host as the original public host and
    # prevents clients from supplying it directly to a Function. Local Services
    # development proxies from loopback without setting VERCEL=1.
    client_host = request.client.host if request.client else ''
    if os.getenv('VERCEL') == '1' or client_host in {'127.0.0.1', '::1'}:
        hosts.add(request.headers.get('x-forwarded-host', '').casefold())
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc) and parsed.netloc.casefold() in hosts


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        seed(db)
        cleanup(db)
    yield


app = FastAPI(title='ScamShield AI', version='1.0.0', description='Shared explainable scam detection. Heuristic scores are not model probabilities.', lifespan=lifespan)
app.add_middleware(BodySizeLimit)
origins = [x.strip() for x in settings.cors_origins.split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type', 'X-ScamShield-Client'])


@app.middleware('http')
async def guard(request: Request, call_next):
    started = time.perf_counter()
    try:
        length = int(request.headers.get('content-length', '0'))
    except ValueError:
        return JSONResponse({'error': {'code': 'invalid_request', 'message': 'Invalid content length.'}}, 400)
    if length > 6 * 1024 * 1024:
        return JSONResponse({'error': {'code': 'too_large', 'message': 'Request exceeds the upload limit.'}}, 413)
    if request.method in {'POST', 'PUT', 'DELETE'}:
        origin = request.headers.get('origin')
        if origin and origin not in origins and not same_origin(request, origin):
            return JSONResponse({'error': {'code': 'forbidden', 'message': 'Request origin is not allowed.'}}, 403)
        if request.headers.get('x-scamshield-client') != 'web':
            return JSONResponse({'error': {'code': 'forbidden', 'message': 'Required client header missing.'}}, 403)
        # Do not trust X-Forwarded-For from arbitrary clients.
        identity = request.client.host if request.client else 'unknown'
        limit = min(settings.rate_limit_per_minute, 10) if '/auth/' in request.url.path else settings.rate_limit_per_minute
        if not limiter.allow(identity + (':auth' if '/auth/' in request.url.path else ':scan'), limit):
            return JSONResponse({'error': {'code': 'rate_limited', 'message': 'Too many requests. Wait a minute and try again.'}}, 429, headers={'Retry-After': '60'})
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Frame-Options'] = 'DENY'
    if settings.environment == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Deliberately exclude request content, full URLs, cookies and IP addresses.
    logger.info(json.dumps({'event': 'request', 'method': request.method, 'route': request.scope.get('route').path if request.scope.get('route') else 'unknown', 'status': response.status_code, 'duration_ms': round((time.perf_counter() - started) * 1000, 1)}))
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse({'error': {'code': str(exc.status_code), 'message': str(exc.detail)}}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Pydantic's default errors contain input values; omit them from responses.
    fields = [{'field': '.'.join(str(x) for x in e['loc']), 'message': e['msg']} for e in exc.errors()]
    return JSONResponse({'error': {'code': 'validation_error', 'message': 'Check your input and try again.', 'fields': fields}}, 422)


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    logger.error(json.dumps({'event': 'internal_error', 'type': type(exc).__name__}))
    return JSONResponse({'error': {'code': 'internal_error', 'message': 'Unable to process this request. Please try again.'}}, 500)


app.include_router(router)
