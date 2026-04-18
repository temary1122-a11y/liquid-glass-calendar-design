# ============================================================
# api/app.py — FastAPI приложение
# ============================================================

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from api.routes import booking, admin
from database.db import init_db
import json

app = FastAPI(title="Lash Bot API", version="1.0.0")

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS настройка для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты
app.include_router(booking.router)
app.include_router(admin.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Детальное логирование ошибок валидации"""

    # Логируем всё что можем о запросе
    print("=" * 80)
    print("VALIDATION ERROR DETAILS:")
    print(f"URL: {request.url}")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")

    # Пытаемся прочитать body
    try:
        body = await request.body()
        print(f"Raw body: {body}")
        try:
            json_body = json.loads(body)
            print(f"Parsed JSON: {json.dumps(json_body, indent=2)}")
        except:
            print("Body is not valid JSON")
    except:
        print("Could not read body")

    # Логируем ошибки Pydantic
    print(f"Validation errors: {exc.errors()}")
    print("=" * 80)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body_received": str(body) if 'body' in locals() else None
        }
    )


@app.on_event("startup")
async def startup_event():
    """Инициализация БД при запуске"""
    init_db()


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {"message": "Lash Bot API", "status": "running"}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}
