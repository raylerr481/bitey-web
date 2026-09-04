from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/workspace/markets", tags=["Bitey Markets"])

SBT_API_ORIGIN = os.getenv(
    "BITEY_SBT_API_ORIGIN",
    "https://bitey-system-bots-trading.raylerr481.workers.dev",
).rstrip("/")


async def _get(path: str) -> Any:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(f"{SBT_API_ORIGIN}{path}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"SBT market service unavailable: {exc}") from exc


@router.get("/status")
async def market_status() -> dict[str, Any]:
    data = await _get("/api/v1/system")
    return {
        "source": "Bitey System Bots Trading",
        "mode": "read_only_context",
        "execution": {"allowed": False, "delegated_to": "sbt_risk_gate"},
        "system": data,
    }


@router.get("/quote/{symbol}")
async def market_quote(symbol: str) -> dict[str, Any]:
    data = await _get(f"/api/v1/mt5/quote/{symbol.upper()}")
    return {
        "source": "Bitey System Bots Trading / MT5",
        "symbol": symbol.upper(),
        "read_only": True,
        "execution": {"allowed": False, "delegated_to": "sbt_risk_gate"},
        "quote": data,
    }
