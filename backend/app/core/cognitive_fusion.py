"""Cognitive fusion primitives for Bitey Brain.

Provider- and database-independent orchestration utilities. They do not claim
that retrieved material is true: sources are normalized, conflicts are surfaced,
and complex requests are converted into bounded executable plans.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable
import re


@dataclass
class EvidenceItem:
    source: str
    content: str
    confidence: float = 0.5
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "content": self.content,
            "confidence": round(max(0.0, min(1.0, self.confidence)), 3),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class Contradiction:
    left: EvidenceItem
    right: EvidenceItem
    reason: str
    severity: str = "medium"

    def as_dict(self) -> dict[str, Any]:
        return {
            "left": self.left.as_dict(),
            "right": self.right.as_dict(),
            "reason": self.reason,
            "severity": self.severity,
        }


@dataclass
class TaskStep:
    id: str
    objective: str
    depends_on: list[str] = field(default_factory=list)
    preferred_tools: list[str] = field(default_factory=list)
    verification_required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "depends_on": self.depends_on,
            "preferred_tools": self.preferred_tools,
            "verification_required": self.verification_required,
        }


class ContradictionEngine:
    """Detects high-signal conflicts without pretending to solve truth itself."""

    NEGATION = re.compile(r"\b(no|not|never|sin|nunca|false|falso|disabled|desactivado)\b", re.I)

    def compare(self, items: Iterable[EvidenceItem]) -> list[Contradiction]:
        evidence = list(items)
        conflicts: list[Contradiction] = []
        for i, left in enumerate(evidence):
            for right in evidence[i + 1 :]:
                if left.source == right.source and left.content == right.content:
                    continue
                if self._conflicts(left.content, right.content):
                    severity = "high" if {left.source, right.source} & {"system", "user", "official"} else "medium"
                    conflicts.append(Contradiction(left, right, "semantic polarity or mutually exclusive claims", severity))
        return conflicts

    def _conflicts(self, left: str, right: str) -> bool:
        a, b = left.strip().lower(), right.strip().lower()
        if not a or not b:
            return False
        # Explicit negation of the same short claim is a useful deterministic signal.
        if a == b:
            return False
        a_core = self.NEGATION.sub("", a).replace("  ", " ").strip()
        b_core = self.NEGATION.sub("", b).replace("  ", " ").strip()
        return a_core == b_core and bool(self.NEGATION.search(a) ^ self.NEGATION.search(b))


class KnowledgeFusionEngine:
    """Fuses memory, graph, research and workspace evidence into one context pack."""

    SOURCE_PRIORITY = {"user": 1.0, "official": 0.95, "system": 0.9, "workspace": 0.85, "graph": 0.8, "memory": 0.65, "web": 0.6, "model": 0.35}

    def __init__(self, contradiction_engine: ContradictionEngine | None = None) -> None:
        self.contradiction_engine = contradiction_engine or ContradictionEngine()

    def fuse(self, sources: dict[str, Iterable[dict[str, Any] | EvidenceItem]] | None = None) -> dict[str, Any]:
        items: list[EvidenceItem] = []
        for source_name, raw_items in (sources or {}).items():
            for raw in raw_items:
                if isinstance(raw, EvidenceItem):
                    item = raw
                else:
                    content = str(raw.get("content") or raw.get("text") or raw.get("value") or "").strip()
                    if not content:
                        continue
                    confidence = float(raw.get("confidence", self.SOURCE_PRIORITY.get(source_name, 0.5)))
                    item = EvidenceItem(source_name, content, confidence, raw.get("timestamp"), dict(raw.get("metadata") or {}))
                items.append(item)
        items.sort(key=lambda x: (x.confidence, self.SOURCE_PRIORITY.get(x.source, 0.5)), reverse=True)
        contradictions = self.contradiction_engine.compare(items)
        return {
            "evidence": [x.as_dict() for x in items],
            "contradictions": [x.as_dict() for x in contradictions],
            "contradiction_count": len(contradictions),
            "confidence": self._aggregate_confidence(items, contradictions),
            "needs_verification": bool(contradictions),
        }

    @staticmethod
    def _aggregate_confidence(items: list[EvidenceItem], contradictions: list[Contradiction]) -> float:
        if not items:
            return 0.0
        base = sum(x.confidence for x in items) / len(items)
        penalty = min(0.45, 0.12 * len(contradictions))
        return round(max(0.0, min(1.0, base - penalty)), 3)


class TaskDecompositionEngine:
    """Creates bounded plans; execution remains controlled by the host system."""

    COMPLEX_MARKERS = ("arquitectura", "analiza", "diseña", "integra", "investiga", "compara", "plan", "debug", "diagnostica", "implementa", "build", "design", "research")

    def decompose(self, message: str, brain_state: dict[str, Any] | None = None) -> dict[str, Any]:
        text = message.strip()
        state = brain_state or {}
        complexity = float(state.get("complexity", 0.0))
        needs_plan = complexity >= 0.55 or sum(1 for marker in self.COMPLEX_MARKERS if marker in text.lower()) >= 2
        if not needs_plan:
            steps = [TaskStep("step-1", "understand and answer the request", [], [], bool(state.get("verification_required", False)))]
        else:
            steps = [
                TaskStep("step-1", "understand request, goals and constraints"),
                TaskStep("step-2", "collect relevant memory, knowledge and evidence", ["step-1"], ["workspace_files", "memory", "web_research"]),
                TaskStep("step-3", "generate candidate reasoning and identify contradictions", ["step-2"], ["code_reasoning"]),
                TaskStep("step-4", "verify high-impact claims and unresolved conflicts", ["step-3"], ["web_research", "calculator"]),
                TaskStep("step-5", "synthesize the answer or bounded action proposal", ["step-4"]),
            ]
        return {
            "task": text,
            "planned": needs_plan,
            "step_count": len(steps),
            "steps": [step.as_dict() for step in steps],
            "execution_policy": "host_and_risk_gate_control_execution",
        }


class CognitiveFusion:
    """Single facade used by Bitey Brain to combine cognition primitives."""

    def __init__(self) -> None:
        self.knowledge = KnowledgeFusionEngine()
        self.decomposition = TaskDecompositionEngine()

    def prepare(self, message: str, *, brain_state: dict[str, Any] | None = None, sources: dict[str, Iterable[dict[str, Any] | EvidenceItem]] | None = None) -> dict[str, Any]:
        fused = self.knowledge.fuse(sources)
        plan = self.decomposition.decompose(message, brain_state)
        return {"knowledge_fusion": fused, "task_plan": plan}

    def status(self) -> dict[str, Any]:
        return {
            "name": "Cognitive Fusion",
            "version": "1.0.0",
            "capabilities": ["evidence_fusion", "contradiction_detection", "task_decomposition"],
            "provider_independent": True,
            "database_independent": True,
            "execution_authority": False,
        }
