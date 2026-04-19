# ============================================================
# api/app.py — FastAPI приложение
# ============================================================

from fastapi import FastAPI, Request, status, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from api.routes import booking, admin
from api.websocket import manager
from database.db import init_db
import json

app = FastAPI(title="Lash Bot API", version="1.0.0")


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to disable HTTP caching for API endpoints"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Disable caching for all API endpoints
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Rate limiter setup
limiter = Limiter(key_func=lambda r: r.client.host if r.client else r.headers.get("x-forwarded-for", ""))
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

# No-cache middleware for API endpoints
app.add_middleware(NoCacheMiddleware)

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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_json()
            # Echo back or handle client messages
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
