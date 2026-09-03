from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from .schemas import NativePlan


class OllamaLanguagePlanner:
    """Local, keyless structured planner. The runtime remains the authority."""

    def __init__(self) -> None:
        self.base_url = os.getenv("BITEY_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("BITEY_OLLAMA_MODEL", "qwen3:4b")
        self.timeout = float(os.getenv("BITEY_OLLAMA_TIMEOUT", "20"))

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return False
                models = response.json().get("models") or []
                return any(str(m.get("name")) == self.model for m in models)
        except Exception:
            return False

    async def plan(self, message: str, context: dict[str, Any] | None = None) -> NativePlan | None:
        if not await self.health():
            return None
        schema = {
            "intent": "string",
            "domain": "string",
            "capabilities": ["web_research|weather|workspace_files|calculator|code_reasoning"],
            "external_information_required": "boolean",
            "freshness_required": "boolean",
            "verification_required": "boolean",
            "search_objective": "string",
            "confidence": "number 0..1",
            "reasons": ["string"],
            "query_strategy": ["string"],
        }
        system = (
            "You are Bitey IA's local language planner. Plan only; never execute tools. "
            "Return ONLY one valid JSON object. Never invent capabilities. The runtime decides what is available. "
            "Use the user's language. If current/external facts are needed, request web_research. "
            f"JSON schema: {json.dumps(schema, ensure_ascii=False)}"
        )
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Request: {message}\nRuntime context: {json.dumps(context or {}, ensure_ascii=False, default=str)[:6000]}"},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
            content = str((data.get("message") or {}).get("content") or "").strip()
            return NativePlan.from_dict(self._extract_json(content))
        except Exception:
            return None

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any]:
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if not match:
                raise
            value = json.loads(match.group(0))
        if not isinstance(value, dict):
            raise ValueError("planner_output_not_object")
        return value
