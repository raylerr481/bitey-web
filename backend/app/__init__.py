"""Bitey IA backend package."""

from fastapi import FastAPI

_original_fastapi_init = FastAPI.__init__


def _bitey_fastapi_init(self, *args, **kwargs):
    _original_fastapi_init(self, *args, **kwargs)
    title = kwargs.get("title")
    if title == "Bitey IA — Cognitive Core" and not getattr(self, "_bitey_workspace_router", False):
        from .workspace_api import router
        self.include_router(router)
        self._bitey_workspace_router = True


FastAPI.__init__ = _bitey_fastapi_init
