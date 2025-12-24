from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from db import connect_to_mongo, close_mongo

app = FastAPI(title="AI Travel Agent – Fast but Modular")

# IMPORTANT: do NOT combine "*" with allow_credentials=True in browsers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)

@app.on_event("startup")
async def _startup():
    await connect_to_mongo()

@app.on_event("shutdown")
async def _shutdown():
    await close_mongo()
