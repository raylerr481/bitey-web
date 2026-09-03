from __future__ import annotations

from typing import Any

from .adapter import NativeLanguageModelAdapter


async def native_planner_status() -> dict[str, Any]:
    return await NativeLanguageModelAdapter().health()
