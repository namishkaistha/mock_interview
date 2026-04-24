"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import session as session_router
from app.routers import tts as tts_router
from app.routers import transcribe as transcribe_router

app = FastAPI(title="Mock Interview API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router.router, prefix="/session")
app.include_router(tts_router.router)
app.include_router(transcribe_router.router)
