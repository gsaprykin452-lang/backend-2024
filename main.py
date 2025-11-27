# FORCE REDEPLOY - $(Get-Date)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Добавь эту хуйню для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React dev сервер
        "http://localhost:5173",    # Vite dev сервер  
        "http://127.0.0.1:3000",    # Localhost альтернативный
        "http://127.0.0.1:5173",    # Vite альтернативный
        "https://gsaprykin452-lang-backend-2024-3498.twc1.net",  # Твой бекенд
        # Добавь сюда URL твоего фронтенда когда задеплоишь
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы (GET, POST, etc.)
    allow_headers=["*"],  # Разрешить все заголовки
)

@app.get("/")
def read_root():
    return {"message": "Server is working!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Добавь еще этот ебучий эндпоинт для теста CORS
@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working, motherfucker!"}