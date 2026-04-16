"""FastAPI application entry point."""
from fastapi import FastAPI
from app.routers import session as session_router

app = FastAPI(title="Mock Interview API")
app.include_router(session_router.router, prefix="/session")
