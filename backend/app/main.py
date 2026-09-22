from contextlib import asynccontextmanager
import asyncio
import time
from uuid import UUID, uuid4
import os
import re
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .background_worker import process_once
from .core.context_engine import ContextEngine
from .core.context_budget import build_context
from .core.cognitive_memory import CognitiveMemoryAdapter
from .core.cognitive_model import CognitiveModel
from .core.bitey_brain import BiteyBrain
from .core.cognitive_trace import CognitiveTraceStore
from .core.evaluation_engine import EvaluationEngine
from .core.module_registry import ModuleRegistry, ModuleSpec
from .core.deep_research import DeepResearchEngine
from .core.learning import LearningEngine
from .core.memory import MemoryStore
from .core.provider_gateway import ProviderGateway
from .core.research_engine import ResearchEngine
from .core.tool_orchestrator import ToolOrchestrator, ToolSpec, safe_calculate
from .core.vector_memory import QdrantVectorMemory
from .core.workspace import WorkspaceStore
from .notifications import send_trainer_test_email
from .schemas import ConversationCreate, MessageCreate, MessageResponse
from .workspace_api import router as workspace_router
from .chat_v2 import create_chat_v2_router

async def _background_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try: await process_once()
        except Exception: pass
        try: await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError: pass

@asynccontextmanager