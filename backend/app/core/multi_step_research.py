from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


@dataclass(frozen=True)
class ResearchSubquestion:
    question: str
    purpose: str
    query: str


@dataclass
class ResearchEvidencePackage:
    original_question: str
    subquestions: list[ResearchSubquestion] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    passes: int = 0
    sufficient: bool = False


class MultiStepResearchRuntime:
    """Bounded planner/orchestrator for evidence-first web research.

    It deliberately does not perform network I/O itself. Search/fetch adapters
    remain responsible for external access, while this runtime plans passes,
    deduplicates evidence, detects simple claim conflicts, and decides whether
    another pass is warranted.
    """

    MAX_SUBQUESTIONS = 5
    MAX_PASSES = 3

    def __init__(self, max_subquestions: int | None = None, max_passes: int | None = None) -> None:
        self.max_subquestions = max(1, min(max_subquestions or self.MAX_SUBQUESTIONS, self.MAX_SUBQUESTIONS))
        self.max_passes = max(1, min(max_passes or self.MAX_PASSES, self.MAX_PASSES))

    def decompose(self, question: str, *, explicit_research: bool = False) -> list[ResearchSubquestion]:
        text = (question or "").strip()
        if not text:
            return []
        candidates = [
            ResearchSubquestion(text, "primary_answer", text),
            ResearchSubquestion(f"¿Qué fuente primaria respalda la respuesta sobre: {text}?", "primary_source", text),
            ResearchSubquestion(f"¿Qué fuentes independientes permiten contrastar: {text}?", "independent_cross_check", text),
        ]
        if explicit_research or len(text) > 140:
            candidates.append(ResearchSubquestion(f"¿Existen contradicciones, riesgos o información no verificada sobre: {text}?", "risk_and_contradictions", text))
        if self._looks_entity_question(text):
            candidates.append(ResearchSubquestion(f"¿Quién está detrás de la entidad o servicio mencionado en: {text}?", "entity_identity", text))
        return candidates[: self.max_subquestions]

    def build_queries(self, subquestions: list[ResearchSubquestion]) -> list[str]:
        seen: set[str] = set()
        queries: list[str] = []
        for item in subquestions:
            query = re.sub(r"\s+", " ", item.query).strip()
            if query and query.lower() not in seen:
                seen.add(query.lower())
                queries.append(query)
        return queries

    def merge_evidence(self, package: ResearchEvidencePackage, items: list[dict[str, Any]], pass_number: int) -> ResearchEvidencePackage:
        known = {str(x.get("url", "")).rstrip("/").lower() for x in package.evidence if x.get("url")}
        for item in items:
            url = str(item.get("url", "")).rstrip("/")
            if url and url.lower() in known:
                continue
            enriched = dict(item)
            enriched["research_pass"] = pass_number
            package.evidence.append(enriched)
            if url:
                known.add(url.lower())
        package.passes = max(package.passes, pass_number)
        package.contradictions = self.detect_contradictions(package.evidence)
        package.sufficient = self.is_sufficient(package)
        return package

    def detect_contradictions(self, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Conservative detector: only flags explicit negation patterns sharing
        # a normalized subject fragment. It avoids pretending semantic certainty.
        statements: list[tuple[str, str]] = []
        for item in evidence:
            text = str(item.get("content") or item.get("snippet") or "").strip()
            url = str(item.get("url") or "")
            if not text or not url:
                continue
            statements.append((url, text.lower()))
        contradictions: list[dict[str, Any]] = []
        for i, (url_a, text_a) in enumerate(statements):
            for url_b, text_b in statements[i + 1 :]:
                if url_a == url_b:
                    continue
                a = self._negation_signature(text_a)
                b = self._negation_signature(text_b)
                if a and b and a[0] == b[0] and a[1] != b[1]:
                    contradictions.append({"subject": a[0], "source_a": url_a, "source_b": url_b, "type": "negation_conflict"})
        return contradictions[:20]

    def is_sufficient(self, package: ResearchEvidencePackage) -> bool:
        good = [x for x in package.evidence if x.get("ok", True) and (x.get("content") or x.get("snippet"))]
        unique_sources = {str(x.get("url")) for x in good if x.get("url")}
        if len(unique_sources) >= 2 and not package.contradictions:
            return True
        return len(unique_sources) >= 3 and len(good) >= 3

    def next_pass_needed(self, package: ResearchEvidencePackage) -> bool:
        return not package.sufficient and package.passes < self.max_passes

    def _looks_entity_question(self, text: str) -> bool:
        return bool(re.search(r"\b(qué es|quien|quién|empresa|plataforma|app|aplicación|servicio|sitio|website|what is|who is)\b", text, re.I))

    def _negation_signature(self, text: str) -> tuple[str, bool] | None:
        patterns = [
            (r"([a-záéíóúñ][a-záéíóúñ0-9 _-]{3,50})\s+(?:no|nunca|jamás)\s+", False),
            (r"([a-záéíóúñ][a-záéíóúñ0-9 _-]{3,50})\s+(?:sí|es|está|tiene)\s+", True),
        ]
        for pattern, polarity in patterns:
            match = re.search(pattern, text)
            if match:
                return (re.sub(r"\s+", " ", match.group(1)).strip(), polarity)
        return None
