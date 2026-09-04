from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .market_api import router as market_router

app = FastAPI(title="Bitey IA — Cognitive Core", version="0.15.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(market_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "bitey-ia", "markets_read_only": True}
