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
    macro_slope: float | None = None
    htf_direction: str | None = None
    regime: str | None = None
    entry_score: float | None = None
    score_gap: float | None = None
    spread_atr_ratio: float | None = None
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
    regime: str = "UNKNOWN"
    next_test: str | None = None
    validation_required: bool = True


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

    def native_structured_analysis(snapshot: TradingSnapshot) -> dict[str, Any]:
        metadata = snapshot.metadata or {}
        turtle = metadata.get("turtle_controller") if isinstance(metadata.get("turtle_controller"), dict) else {}
        signal = str(turtle.get("signal") or metadata.get("signal") or "").upper()
        regime = str(turtle.get("regime") or snapshot.regime or "UNKNOWN").upper()
        strategy = str(turtle.get("strategy") or metadata.get("strategy") or "TURTLE").upper()
        mode = str(metadata.get("mt4_reported_mode") or metadata.get("mt4_account_mode") or "UNKNOWN").upper()
        if signal in {"BUY", "SELL"}:
            action = signal
            confidence = 0.70 if regime not in {"UNKNOWN", "RANGING"} else 0.55
            reason = f"MT4/SBT Turtle Controller reports an actionable {signal} signal. Regime={regime}; mode={mode}. Advisory only; the local MT4 Risk Gate remains authoritative."
        else:
            action = "HOLD"
            confidence = 0.35 if regime != "UNKNOWN" else 0.20
            reason = f"No actionable Turtle signal is currently reported by MT4/SBT. Regime={regime}; mode={mode}. Continue observing and validate the next research candidate."
        next_test = "TURTLE_S1_M30" if snapshot.timeframe.upper() == "H1" else "TURTLE_S1_H1"
        return {
            "ok": True, "mode": "analysis_only", "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe, "action": action,
            "confidence": confidence, "risk_allowed": False,
            "strategy": strategy[:120], "reason": reason[:1000],
            "source": "bitey_native_trading_reasoner",
            "execution_boundary": "mt4_local_risk_gate",
            "regime": regime[:64], "next_test": next_test,
            "validation_required": True,
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
            start = clean.find("{")
            end = clean.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("trading_provider_returned_no_json_object")
            data = json.loads(clean[start : end + 1])
            if not isinstance(data, dict):
                raise ValueError("trading_provider_returned_non_object")
            action = str(data.get("action", "HOLD")).upper()
            if action not in {"BUY", "SELL", "HOLD"}:
                action = "HOLD"
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
            risk_allowed = bool(data.get("risk_allowed", False)) and action != "HOLD"
            native = native_structured_analysis(snapshot)
            return TradingAnalysisResponse(
                ok=True,
                mode="analysis_only",
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe,
                action=action,
                confidence=confidence,
                risk_allowed=risk_allowed,
                strategy=str(data.get("strategy", native["strategy"]))[:120],
                reason=str(data.get("reason", native["reason"]))[:1000],
                source=str(context.get("provider_selected") or "bitey_provider_gateway"),
                execution_boundary="mt4_local_risk_gate",
                regime=str(data.get("regime", native["regime"]))[:64],
                next_test=str(data.get("next_test", native["next_test"]))[:120],
                validation_required=True,
            )
        except Exception:
            return TradingAnalysisResponse(**native_structured_analysis(snapshot))

    return router
