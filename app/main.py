from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.upload_routes import router as prescriptions_router


app = FastAPI(title="Personal Intel")
app.include_router(prescriptions_router, prefix="/api")
app.mount("/", StaticFiles(directory="static", html=True), name="static")