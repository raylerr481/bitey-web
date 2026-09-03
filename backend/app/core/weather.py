from __future__ import annotations

import re
from typing import Any

import httpx


class WeatherEngine:
    """Free-first weather capability using Open-Meteo (no API key required)."""

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    async def current(self, query: str) -> dict[str, Any]:
        location = await self._geocode(query)
        if not location:
            return {"ok": False, "available": True, "error": "location_not_found"}

        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m",
            "timezone": "auto",
            "forecast_days": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(self.FORECAST_URL, params=params)
                response.raise_for_status()
                data = response.json()
            return {
                "ok": True,
                "available": True,
                "provider": "open-meteo",
                "location": {
                    "name": location.get("name"),
                    "country": location.get("country"),
                    "admin1": location.get("admin1"),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                },
                "timezone": data.get("timezone"),
                "current": data.get("current") or {},
                "source_url": self.FORECAST_URL,
            }
        except Exception as exc:
            return {"ok": False, "available": True, "provider": "open-meteo", "error": type(exc).__name__}

    async def _geocode(self, query: str) -> dict[str, Any] | None:
        cleaned = query.replace("¿", " ").replace("?", " ").strip()
        params = {"name": cleaned[:120], "count": 5, "language": "es", "format": "json"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.GEOCODING_URL, params=params)
                response.raise_for_status()
                results = response.json().get("results") or []
                if not results:
                    match = re.search(r"(?:tiempo|clima|temperatura|weather)\s+(?:en|de|em|in)\s+(.+)", cleaned, re.I)
                    if match:
                        params["name"] = match.group(1).strip()[:80]
                        response = await client.get(self.GEOCODING_URL, params=params)
                        response.raise_for_status()
                        results = response.json().get("results") or []
            return results[0] if results else None
        except Exception:
            return None

    @staticmethod
    def describe(result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return "No fue posible obtener el tiempo en este momento."
        loc = result.get("location") or {}
        cur = result.get("current") or {}
        return (
            f"Tiempo actual en {loc.get('name') or 'la ubicación solicitada'}: "
            f"{cur.get('temperature_2m')} °C, sensación {cur.get('apparent_temperature')} °C, "
            f"humedad {cur.get('relative_humidity_2m')}%, viento {cur.get('wind_speed_10m')} km/h, "
            f"lluvia {cur.get('rain')} mm. Fuente: Open-Meteo."
        )
