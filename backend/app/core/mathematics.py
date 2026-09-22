from __future__ import annotations
import math
import re
from statistics import mean, median, pstdev
from typing import Any

NUMBER = r"[-+]?\d+(?:[.,]\d+)?"

def _nums(text: str) -> list[float]:
    return [float(x.replace(",", ".")) for x in re.findall(NUMBER, text)]

def calculate(text: str) -> dict[str, Any]:
    s = text.strip().replace(",", ".")
    # Deterministic arithmetic only; no eval.
    if not re.fullmatch(r"[0-9.\s()+\-*/%^]+", s):
        return {"ok": False, "error": "unsupported_expression"}
    try:
        from .tool_orchestrator import safe_calculate
        value = safe_calculate(s)
        return {"ok": True, "operation": "arithmetic", "result": value, "formula": s}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}

def analyze(text: str) -> dict[str, Any]:
    s = text.lower()
    nums = _nums(text)
    if not nums:
        return {"ok": False, "error": "no_numeric_input"}

    if any(k in s for k in ("promedio", "media", "average", "mean")):
        return {"ok": True, "operation": "mean", "result": mean(nums), "inputs": nums}
    if any(k in s for k in ("mediana", "median")):
        return {"ok": True, "operation": "median", "result": median(nums), "inputs": nums}
    if any(k in s for k in ("desviación", "desviacion", "standard deviation", "desvio")):
        return {"ok": True, "operation": "population_stddev", "result": pstdev(nums), "inputs": nums}
    if any(k in s for k in ("porcentaje", "percent", "%")) and len(nums) >= 2:
        base, value = nums[0], nums[1]
        if base == 0:
            return {"ok": False, "error": "division_by_zero"}
        return {"ok": True, "operation": "percentage", "result": value / base * 100, "base": base, "value": value}
    if any(k in s for k in ("cagr", "crecimiento anual compuesto")) and len(nums) >= 3:
        initial, final, years = nums[:3]
        if initial <= 0 or years <= 0:
            return {"ok": False, "error": "invalid_cagr_inputs"}
        return {"ok": True, "operation": "cagr", "result": (final / initial) ** (1 / years) - 1, "initial": initial, "final": final, "years": years}
    if any(k in s for k in ("probabilidad", "probability")) and len(nums) >= 2:
        successes, trials = nums[:2]
        if trials <= 0 or successes < 0 or successes > trials:
            return {"ok": False, "error": "invalid_probability_inputs"}
        return {"ok": True, "operation": "probability", "result": successes / trials, "successes": successes, "trials": trials}
    if any(k in s for k in ("suma", "sum", "total")):
        return {"ok": True, "operation": "sum", "result": sum(nums), "inputs": nums}
    if len(nums) >= 2 and any(op in text for op in ("+", "-", "*", "/", "^", "%")):
        return {"ok": False, "error": "use_explicit_arithmetic_expression"}
    return {"ok": True, "operation": "descriptive_statistics", "count": len(nums), "sum": sum(nums), "mean": mean(nums), "median": median(nums), "stddev": pstdev(nums) if len(nums) > 1 else 0.0, "min": min(nums), "max": max(nums)}

def research_metrics(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0}
    return {"count": len(values), "mean": mean(values), "median": median(values), "stddev": pstdev(values) if len(values) > 1 else 0.0, "min": min(values), "max": max(values)}
