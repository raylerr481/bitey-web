from __future__ import annotations

import logging
import os
import time
from typing import Any, Protocol

import httpx

from .free_provider_policy import can_use_external_free_provider, cloud_allowed, env_true, free_only_mode, hard_stop, openrouter_model_is_free, openrouter_pricing_is_zero
from .native_model import NativeReasoningModel
from .ollama_provider import OllamaProvider

logger = logging.getLogger("bitey.providers")

class AIProvider(Protocol):
    name: str
    priority: int
    free_only: bool
    async def health(self) -> bool: ...
    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str: ...

class OpenAICompatibleProvider:
    def __init__(self, name: str, endpoint: str, model: str, api_key: str, priority: int, free_only: bool = True) -> None:
        self.name=name; self.endpoint=endpoint.rstrip("/"); self.model=model; self.api_key=api_key.strip(); self.priority=priority; self.free_only=free_only
    async def health(self) -> bool: return bool(self.api_key or self.endpoint.startswith("http://127.0.0.1") or self.endpoint.startswith("http://localhost"))
    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not await self.health(): raise RuntimeError("provider_not_configured")
        payload={"model":self.model,"messages":messages,"temperature":0.2,"max_tokens":int(os.getenv("AI_MAX_OUTPUT_TOKENS","1200"))}
        headers={"Content-Type":"application/json"}
        if self.api_key: headers["Authorization"]=f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=float(os.getenv("AI_REQUEST_TIMEOUT","45"))) as client:
            response=await client.post(f"{self.endpoint}/chat/completions",headers=headers,json=payload); response.raise_for_status(); data=response.json()
        choices=data.get("choices") or []
        if not choices or not choices[0].get("message",{}).get("content"): raise RuntimeError("empty_response")
        return str(choices[0]["message"]["content"]).strip()

class CloudflareAIProvider:
    def __init__(self, model: str, account_id: str, api_token: str, priority: int) -> None:
        self.name="cloudflare-paid-or-plan-dependent"; self.model=model; self.account_id=account_id.strip(); self.api_token=api_token.strip(); self.priority=priority; self.free_only=False
    async def health(self) -> bool: return bool(self.account_id and self.api_token)
    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not await self.health(): raise RuntimeError("provider_not_configured")
        prompt="\n".join(f"{m['role']}: {m['content']}" for m in messages)
        url=f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"
        headers={"Authorization":f"Bearer {self.api_token}","Content-Type":"application/json"}
        async with httpx.AsyncClient(timeout=float(os.getenv("AI_REQUEST_TIMEOUT","45"))) as client:
            response=await client.post(url,headers=headers,json={"messages":messages,"prompt":prompt}); response.raise_for_status(); data=response.json()
        result=data.get("result") or {}; return str(result.get("response") or result.get("text") or "").strip()

class ProviderGateway:
    """Model execution only: Bitey decides the inference role before this layer runs."""
    ROLE_PREFERENCES={
        "strong_reasoning_synthesis":("ollama-local","bitey-native-cognitive-v1"),
        "evidence_grounded_synthesis":("ollama-local","bitey-native-cognitive-v1"),
        "code_reasoning":("ollama-local","bitey-native-cognitive-v1"),
        "guarded_analysis":("bitey-native-cognitive-v1","ollama-local"),
        "fast_synthesis":("ollama-local","bitey-native-cognitive-v1"),
        "synthesis":("ollama-local","bitey-native-cognitive-v1"),
    }
    def __init__(self) -> None:
        self._providers={}; self._openrouter_catalog_loaded=False; self._openrouter_catalog_loaded_at=0.0; self._conversation_provider={}; self._register_from_environment()
    def register(self, provider):
        if free_only_mode() and not provider.free_only: logger.info("provider_rejected_free_only provider=%s",provider.name); return
        self._providers[provider.name]=provider
    async def _register_external_free_providers(self):
        if not cloud_allowed() or not free_only_mode(): return
        if env_true("GROQ_ENABLED",False) and os.getenv("GROQ_API_KEY"):
            model=os.getenv("GROQ_MODEL","openai/gpt-oss-120b")
            if can_use_external_free_provider("groq",model=model): self.register(OpenAICompatibleProvider("groq-free","https://api.groq.com/openai/v1",model,os.getenv("GROQ_API_KEY",""),int(os.getenv("GROQ_PRIORITY","50")),True))
        if env_true("OPENROUTER_ENABLED",False) and os.getenv("OPENROUTER_API_KEY"):
            qwen=os.getenv("OPENROUTER_QWEN_MODEL","qwen/qwen3-4b:free"); deepseek=os.getenv("OPENROUTER_DEEPSEEK_MODEL","deepseek/deepseek-chat-v3-0324:free")
            if can_use_external_free_provider("openrouter",model=qwen): self.register(OpenAICompatibleProvider("qwen-free","https://openrouter.ai/api/v1",qwen,os.getenv("OPENROUTER_API_KEY",""),60,True))
            if env_true("DEEPSEEK_ENABLED",True) and can_use_external_free_provider("openrouter",model=deepseek): self.register(OpenAICompatibleProvider("deepseek-free","https://openrouter.ai/api/v1",deepseek,os.getenv("OPENROUTER_API_KEY",""),70,True))
    def _register_from_environment(self):
        if env_true("OLLAMA_ENABLED",True): self.register(OllamaProvider())
        if env_true("BITEY_NATIVE_MODEL_ENABLED",True):
            native=NativeReasoningModel(); native.priority=2; self.register(native)
        if env_true("GEMMA_4_12B_ENABLED",False):
            endpoint=os.getenv("GEMMA_4_12B_ENDPOINT","http://127.0.0.1:50305/v1")
            self.register(OpenAICompatibleProvider("gemma-4-12b-local",endpoint,os.getenv("GEMMA_4_12B_MODEL","google/gemma-4-12B-it"),os.getenv("GEMMA_4_12B_API_KEY",""),int(os.getenv("GEMMA_4_12B_PRIORITY","3")),endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost")))
        if cloud_allowed() and not free_only_mode() and env_true("CLOUDFLARE_AI_ENABLED",True):
            account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID",""); token=os.getenv("CLOUDFLARE_API_TOKEN","")
            if account_id and token: self.register(CloudflareAIProvider(os.getenv("CLOUDFLARE_AI_MODEL","@cf/qwen/qwen3-0.6b"),account_id,token,int(os.getenv("CLOUDFLARE_PRIORITY","80"))))
    @staticmethod
    def _is_free_model_id(model_id): return openrouter_model_is_free(model_id)
    @staticmethod
    def _is_chat_model(item):
        architecture=item.get("architecture") or {}; inputs={str(x).lower() for x in (architecture.get("input_modalities") or ["text"])}; outputs={str(x).lower() for x in (architecture.get("output_modalities") or ["text"])}
        return "text" in inputs and "text" in outputs
    async def _discover_openrouter_free_models(self):
        if not cloud_allowed() or not free_only_mode(): return
        refresh_seconds=max(30,int(os.getenv("OPENROUTER_CATALOG_REFRESH_SECONDS","900")))
        if self._openrouter_catalog_loaded and time.monotonic()-self._openrouter_catalog_loaded_at < refresh_seconds: return
        api_key=os.getenv("OPENROUTER_API_KEY","").strip()
        if not api_key or not env_true("OPENROUTER_ENABLED",False): return
        try:
            async with httpx.AsyncClient(timeout=float(os.getenv("OPENROUTER_CATALOG_TIMEOUT","12"))) as client:
                response=await client.get("https://openrouter.ai/api/v1/models",headers={"Authorization":f"Bearer {api_key}"}); response.raise_for_status(); data=response.json()
            priority=int(os.getenv("OPENROUTER_DISCOVERED_PRIORITY","90")); discovered=set()
            for item in data.get("data") or []:
                model_id=str(item.get("id") or "")
                if not self._is_free_model_id(model_id) or not openrouter_pricing_is_zero(item) or not self._is_chat_model(item): continue
                name="openrouter-free-"+model_id.replace("/","-").replace(":","-"); self.register(OpenAICompatibleProvider(name,"https://openrouter.ai/api/v1",model_id,api_key,priority,True)); discovered.add(name); priority+=1
            for name in [n for n in self._providers if n.startswith("openrouter-free-") and n not in discovered]: self._providers.pop(name,None)
            self._openrouter_catalog_loaded=True; self._openrouter_catalog_loaded_at=time.monotonic()
        except Exception as exc:
            self._openrouter_catalog_loaded=True; self._openrouter_catalog_loaded_at=time.monotonic(); logger.warning("openrouter_catalog_discovery_failed error=%s",type(exc).__name__)
    async def _prepare_external_free_providers(self):
        if cloud_allowed() and free_only_mode(): await self._discover_openrouter_free_models(); await self._register_external_free_providers()
    def available(self): return [p.name for p in sorted(self._providers.values(),key=lambda p:p.priority)]
    def _order_for_role(self,providers,role):
        preferred=self.ROLE_PREFERENCES.get(role,self.ROLE_PREFERENCES["synthesis"]); rank={name:i for i,name in enumerate(preferred)}
        return sorted(providers,key=lambda p:(rank.get(p.name,100),p.priority))
    async def generate(self, *, messages, context):
        await self._prepare_external_free_providers()
        providers=[p for p in self._providers.values() if not free_only_mode() or p.free_only]
        if not providers: return "Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos." if hard_stop() and free_only_mode() else "Bitey IA no tiene un proveedor disponible en este momento."
        conversation_id=str(context.get("conversation_id") or "").strip(); brain=context.get("bitey_brain") or {}; role=str(brain.get("model_role") or context.get("model_role") or "synthesis")
        ordered=self._order_for_role(providers,role); sticky_name=self._conversation_provider.get(conversation_id) if conversation_id else None; sticky=next((p for p in ordered if p.name==sticky_name),None) if sticky_name else None
        if sticky: ordered=[sticky]+[p for p in ordered if p.name!=sticky.name]
        attempted=set(); max_providers=max(1,int(os.getenv("AI_COUNCIL_MAX_PROVIDERS","3")))
        for attempt,provider in enumerate(ordered[:max_providers],1):
            attempted.add(provider.name)
            try:
                if not await provider.health(): continue
                answer=await provider.generate(messages=messages,context={**context,"bitey_model_role":role})
                if answer:
                    if conversation_id: self._conversation_provider[conversation_id]=provider.name
                    logger.info("provider_selected provider=%s role=%s attempt=%d",provider.name,role,attempt); return answer
            except Exception as exc:
                logger.warning("provider_failed provider=%s role=%s attempt=%d error=%s",provider.name,role,attempt,type(exc).__name__)
                if conversation_id and self._conversation_provider.get(conversation_id)==provider.name: self._conversation_provider.pop(conversation_id,None)
        native=self._providers.get("bitey-native-cognitive-v1")
        if native and native.name not in attempted and (not free_only_mode() or native.free_only):
            try:
                answer=await native.generate(messages=messages,context={**context,"bitey_model_role":role})
                if answer: return answer
            except Exception as exc: logger.warning("native_model_failed error=%s",type(exc).__name__)
        return "Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos."
