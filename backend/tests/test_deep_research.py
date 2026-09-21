import asyncio
from types import SimpleNamespace

from backend.app.core.deep_research import DeepResearchEngine


def test_knowledge_fallback_retries_wikipedia_after_discovered_pages_fail(monkeypatch):
    engine = DeepResearchEngine()
    plan = engine.plan("¿Qué es el mercado?", {})
    discovered = "https://example.com/blocked"
    wikipedia = "https://en.wikipedia.org/wiki/Market"

    class FakeResponse:
        def __init__(self, url):
            self.url = url
            self.headers = {"content-type": "text/html"}
            self.content = (
                b"<html><title>Market</title><body>"
                + b"Mercado es un sistema donde se encuentran compradores y vendedores. " * 5
                + b"</body></html>"
            )

        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            if url == discovered:
                raise RuntimeError("blocked")
            if "wikipedia.org/w/api.php" in url:
                return SimpleNamespace(
                    raise_for_status=lambda: None,
                    json=lambda: {"query": {"search": [{"title": "Market"}]}},
                )
            if url == wikipedia:
                return FakeResponse(url)
            raise RuntimeError(f"unexpected url: {url}")

    async def fake_search(*args, **kwargs):
        return [discovered]

    async def fake_wikipedia(*args, **kwargs):
        return [wikipedia]

    monkeypatch.setattr("backend.app.core.deep_research.httpx.AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(engine, "_search", fake_search)
    monkeypatch.setattr(engine, "_search_wikipedia", fake_wikipedia)

    result = asyncio.run(engine.fetch(plan))
    assert any(e.ok and e.url == wikipedia for e in result.evidence)
