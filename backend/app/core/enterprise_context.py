"""Generic enterprise context adapter inspired by the BiteFixes company layer.

Bitey IA owns the orchestration. Enterprise context is tenant-scoped data that
can be supplied by a channel or loaded from an optional Supabase company
profile. No BiteFixes identity is hard-coded here.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


class EnterpriseContextResolver:
    """Resolve optional company context without making it a hard dependency."""

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.company_table = os.getenv("BITEY_COMPANY_TABLE", "companies")
        self.profile_table = os.getenv("BITEY_COMPANY_PROFILE_TABLE", "company_ai_profiles")
        self.timeout = max(0.5, float(os.getenv("BITEY_COMPANY_CONTEXT_TIMEOUT", "2.0")))

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)

    def resolve(self, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve enterprise context from request metadata, env JSON, or Supabase.

        Request metadata wins, allowing every channel to provide a tenant profile
        without coupling Bitey Web to one company. Supabase loading is optional
        and failure is deliberately non-fatal so existing chat keeps working.
        """
        supplied = metadata.get("enterprise")
        if isinstance(supplied, dict) and supplied:
            return self._normalize(supplied, source="request")

        raw_profile = os.getenv("BITEY_ENTERPRISE_PROFILE_JSON", "").strip()
        if raw_profile:
            try:
                profile = json.loads(raw_profile)
                if isinstance(profile, dict):
                    return self._normalize(profile, source="environment")
            except json.JSONDecodeError:
                pass

        company_id = metadata.get("company_id") or metadata.get("enterprise_company_id")
        if company_id and self.configured:
            loaded = self._load_company(str(company_id))
            if loaded:
                return loaded
        return None

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def _get(self, table: str, company_id: str) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.url}/rest/v1/{table}",
                    headers=self._headers(),
                    params={"company_id": f"eq.{company_id}", "select": "*", "limit": "1"},
                )
                if response.status_code >= 400:
                    return None
                rows = response.json()
                return rows[0] if isinstance(rows, list) and rows else None
        except Exception:
            return None

    def _load_company(self, company_id: str) -> dict[str, Any] | None:
        company = self._get(self.company_table, company_id)
        profile = self._get(self.profile_table, company_id)
        if not company and not profile:
            return None
        profile_data = profile.get("profile") if isinstance(profile, dict) else {}
        if not isinstance(profile_data, dict):
            profile_data = {}
        return self._normalize(
            {
                "company_id": company_id,
                "company": company or {},
                "company_name": (profile or {}).get("company_name") or (company or {}).get("name"),
                "description": (profile or {}).get("description") or "",
                "industry": (profile or {}).get("industry") or "",
                "profile": profile_data,
                "website": profile_data.get("website") or (company or {}).get("website"),
                "services": profile_data.get("services") or [],
                "locations": profile_data.get("locations") or [],
                "objectives": profile_data.get("objectives") or [],
                "directives": {**(profile_data.get("behavior") or {}), **(profile_data.get("governance") or {})},
                "authoritative": True,
            },
            source="supabase",
        )

    def _normalize(self, value: dict[str, Any], *, source: str) -> dict[str, Any]:
        return {
            "company_id": value.get("company_id") or value.get("id"),
            "company_name": str(value.get("company_name") or value.get("name") or "").strip(),
            "description": str(value.get("description") or "").strip(),
            "industry": str(value.get("industry") or "").strip(),
            "website": str(value.get("website") or value.get("website_url") or "").strip(),
            "services": value.get("services") if isinstance(value.get("services"), list) else [],
            "locations": value.get("locations") if isinstance(value.get("locations"), list) else [],
            "objectives": value.get("objectives") if isinstance(value.get("objectives"), list) else [],
            "directives": value.get("directives") if isinstance(value.get("directives"), dict) else {},
            "profile": value.get("profile") if isinstance(value.get("profile"), dict) else {},
            "source": source,
            "authoritative": bool(value.get("authoritative", source == "supabase")),
        }
