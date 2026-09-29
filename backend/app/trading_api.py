from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .core.provider_gateway import ProviderGateway, sanitize_public_answer


class TradingSnapshot(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=16)
    timestamp: str | None = None
    bid: float | None = None
    ask: float | None = None
    spread_points: float | None = None
    atr_points: float | None = None
    adx: float | None = None
    rsi: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    ema_macro: float | None = None
    close: float | None = None
    previous_close: float | None = None
    macro_slope: str | None = None
    htf_direction: str | None = None
    regime: str | None = None
    entry_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TradingAnalysisResponse(BaseModel):
    ok: bool
    mode: str
    symbol: str
    timeframe: str
    action: str
    confidence: float
    risk_allowed: bool
    strategy: str
    reason: str
    source: str
    execution_boundary: str = "mt4_local_risk_gate"


def create_trading_router(providers: ProviderGateway) -> APIRouter:
    router = APIRouter(prefix="/api/v2/trading", tags=["trading"])

    @router.get("/capabilities")
    async def trading_capabilities() -> dict[str, Any]:
        return {
            "enabled": True,
            "mode": "analysis_only",
            "market_snapshot": True,
            "structured_signal": True,
            "live_order_execution": False,
            "execution_boundary": "mt4_local_risk_gate",
            "providers": providers.available(),
        }

    @router.post("/analyze", response_model=TradingAnalysisResponse)
    async def analyze(
        snapshot: TradingSnapshot,
        x_trading_module_token: str | None = Header(default=None),
    ) -> TradingAnalysisResponse:
        expected = os.getenv("TRADING_MODULE_TOKEN", "").strip()
        if expected and x_trading_module_token != expected:
            raise HTTPException(status_code=401, detail="invalid_trading_module_token")

        payload = snapshot.model_dump(exclude_none=True)
        prompt = (
            "You are Bitey IA's trading analysis module. Analyze the supplied MT4 "
            "market snapshot. This is advisory/read-only analysis only. Never place "
            "or request an order. Return ONLY compact JSON with exactly these keys: "
            "action (BUY|SELL|HOLD), confidence (0..1), risk_allowed (boolean), "
            "strategy, reason. Do not invent missing values. A local MT4 Risk Gate "
            "has final authority over execution.\n\n"
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        context = {
            "conversation_id": f"trading:{snapshot.symbol}:{snapshot.timeframe}",
            "current_intent_domain": "trading",
            "model_role": "guarded_analysis",
            "bitey_brain": {
                "model_role": "guarded_analysis",
                "risk_level": "high",
            },
        }
        try:
            raw = await providers.generate(
                messages=[
                    {"role": "system", "content": "Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                context=context,
            )
            clean = sanitize_public_answer(raw)
            data = json.loads(clean)
            action = str(data.get("action", "HOLD")).upper()
            if action not in {"BUY", "SELL", "HOLD"}:
                action = "HOLD"
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
            risk_allowed = bool(data.get("risk_allowed", False)) and action != "HOLD"
            return TradingAnalysisResponse(
                ok=True,
                mode="analysis_only",
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe,
                action=action,
                confidence=confidence,
                risk_allowed=risk_allowed,
                strategy=str(data.get("strategy", "advisory"))[:120],
                reason=str(data.get("reason", "No actionable analysis returned."))[:1000],
                source=str(context.get("provider_selected") or "bitey_provider_gateway"),
            )
        except Exception:
            return TradingAnalysisResponse(
                ok=False,
                mode="analysis_only",
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe,
                action="HOLD",
                confidence=0.0,
                risk_allowed=False,
                strategy="none",
                reason="Trading analysis unavailable; local MT4 Risk Gate must reject execution.",
                source="safe_fallback",
            )

    return router
