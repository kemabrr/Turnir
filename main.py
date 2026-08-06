"""FastAPI Backend - PUBG Turnir"""
import os
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import engine, Base
from routers import auth, profile, payment, teams, turnir, admin, lobi, magazyn

# Tablisalary döret
Base.metadata.create_all(bind=engine)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="PUBG Turnir API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG") else None,
    redoc_url=None
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Cloudflare Pages üçin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerlary goş
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(payment.router)
app.include_router(teams.router)
app.include_router(turnir.router)
app.include_router(admin.router)
app.include_router(lobi.router)
app.include_router(magazyn.router)


@app.get("/")
def home():
    return {
        "message": "Backend işleýär!",
        "status": "ok",
        "version": "1.0.0"
    }


# ---------- ERROR HANDLERS ----------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ähli 'raise HTTPException(...)' -lary {success:false, message:...} görnüşine getir.
    Bu bolmasa FastAPI ustunlik bilen {"detail": ...} iberyar, we frontend-in
    result.message hemmesi 'undefined' bolup, hakyky sebäp gizlenýär."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic validasiýa ýalňyşlyklaryny-da (422) message görnüşine getir."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    msg = first.get("msg", "Maglumatlar nädogry")
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": f"{field}: {msg}" if field else msg}
    )

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "message": "Sahypa tapylmady"}
    )

@app.exception_handler(500)
async def server_error(request: Request, exc):
    logger.error(f"500: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Serwer ýalňyşlygy"}
    )

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={"success": False, "message": "Gaty köp synanyşyk!"}
    )
