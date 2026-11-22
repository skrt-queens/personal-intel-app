from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers.auth_routes import router as auth_router
from app.routers.upload_routes import router as prescriptions_router


app = FastAPI(title="Personal Intel")
init_db()
app.include_router(auth_router, prefix="/api")
app.include_router(prescriptions_router, prefix="/api")
app.mount("/", StaticFiles(directory="static", html=True), name="static")