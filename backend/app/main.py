
if os.getenv("BITEFIXES_MODULE_ENABLED", "false").lower() == "true":
    modules.register(ModuleSpec("bitefixes", "Specialized business/support module exposed through an external API contract.", os.getenv("BITEFIXES_MODULE_URL"), ("business_support", "crm", "tickets", "customer_context"), metadata={"integration_type":"external_specialized","role":"external_specialized_module","owner":"bitefixes","domain":"business_support"}))

async def web_research_tool(message: str, context: dict | None = None) -> dict:
    plan = await deep_research.fetch(deep_research.plan(message, context or {}))
    sources = deep_research.source_summary(plan)
    usable = [e for e in plan.evidence if e.ok and e.content and e.url]
    hosts = {urlparse(e.url).hostname.lower().removeprefix("www.") for e in usable if urlparse(e.url).hostname}
    import re
    field_values: dict[str, dict[str, set[str]]] = {}
    for item in usable:
        host = urlparse(item.url).hostname.lower().removeprefix("www.")
        for match in re.finditer(r"(?im)^\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 _/-]{1,40})\s*[:=-]\s*(\d+(?:[.,]\d+)?(?:%|°C|\s?(?:km/h|USD|EUR|BRL))?)\s*$", item.content):
            label = re.sub(r"\s+", " ", match.group(1).strip().lower())
            value = match.group(2).strip().lower()
            field_values.setdefault(label, {}).setdefault(host, set()).add(value)
    conflicts = []
    for label, by_host in field_values.items():
        if len(by_host) < 2:
            continue
        values = sorted({value for vals in by_host.values() for value in vals})
        if len(values) > 1:
            conflicts.append({"field": label, "values": values, "hosts": sorted(by_host)})
    return {
        "ok": bool(usable),
        "reasons": plan.reasons,
        "sources": sources,
        "results": [
            {**source, "evidence_verified": bool(source.get("ok")),
             "page_evidence": next((e.content[:5000] for e in usable if e.url == source.get("url")), ""),
             "source_quality": 0.65, "source_category": "web_source"}
            for source in sources
        ],
        "evidence": deep_research.evidence_context(plan),
        "verified_evidence_count": len(usable),
        "verified_source_host_count": len(hosts),
        "discovery_result_count": len(sources),
        "conflict_detected": bool(conflicts),
        "conflict_candidates": conflicts[:12],
    }
async def workspace_files_tool(message: str, context: dict | None = None) -> dict: return {"ok": True, "available": True, "note": "Project files are handled through the general workspace layer."}
async def calculator_tool(message: str, context: dict | None = None) -> dict: