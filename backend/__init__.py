from fastapi import APIRouter

from backend.app.routers import pydatabase, pytable, auth

run = APIRouter()

run.include_router(auth.router)
run.include_router(pydatabase.router)
run.include_router(pytable.router)