"""
Daily Digest - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="Daily Digest API",
    description="AI приложение для утренних брифингов",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Daily Digest API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# API Routers
try:
    from app.api import auth, data_sources, briefings, users
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(data_sources.router, prefix="/api/v1/sources", tags=["data-sources"])
    app.include_router(briefings.router, prefix="/api/v1/briefings", tags=["briefings"])
except Exception as e:
    print(f"Warning: Could not load some routers: {e}")
    # Загружаем хотя бы auth для тестирования
    try:
        from app.api import auth
        app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    except:
        pass

