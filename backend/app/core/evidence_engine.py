from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
import re


@dataclass
class EvidenceAssessment:
    url: str
    usable: bool
    source_reliability: float
    freshness: float
    directness: float
    quality: float
    signals: list[str] = field(default_factory=list)


@dataclass
class EvidenceDecision:
    sufficient: bool
    confidence: float
    agreement: float
    contradiction_detected: bool
    assessments: list[EvidenceAssessment] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class EvidenceEngine:
    """Deterministic evidence gate owned by Bitey, independent of LLM providers.

    It scores provenance, source reliability, freshness and directness, then
    checks coarse cross-source agreement/contradiction signals. It does not
    generate conclusions; it decides whether collected evidence is strong
    enough to support a downstream conclusion.
    """

    TRUSTED_DOMAINS = {
        "python.org": 0.98,
        "docs.python.org": 0.99,
        "developer.mozilla.org": 0.97,
        "wikipedia.org": 0.82,
        "github.com": 0.92,
        "microsoft.com": 0.95,
        "google.com": 0.94,
        "openai.com": 0.94,
        "supabase.com": 0.95,
    }
    LOW_TRUST_MARKERS = ("blogspot.", "wordpress.com", "medium.com")
    CONTRADICTION_MARKERS = (
        " however ", " but ", " contrary ", " contradict", " differs ",
        " not ", " no longer ", " instead ", " although ",
    )

    def assess(self, query: str, evidence: list[dict[str, Any]]) -> EvidenceDecision:
        assessments: list[EvidenceAssessment] = []
        usable = [item for item in evidence if item.get("ok") and item.get("content")]
        for item in usable:
            url = str(item.get("url") or "")
            content = str(item.get("content") or "")
            reliability = self._source_reliability(url)
            freshness = self._freshness(query, content)
            directness = self._directness(query, content)
            quality = round(0.40 * reliability + 0.25 * freshness + 0.35 * directness, 3)
            signals = ["usable_content"]
            if reliability >= 0.9:
                signals.append("high_reliability_source")
            if freshness >= 0.8:
                signals.append("freshness_supported")
            if directness >= 0.8:
                signals.append("direct_match")
            assessments.append(EvidenceAssessment(url, True, reliability, freshness, directness, quality, signals))

        agreement, contradiction = self._cross_source_signal(query, usable)
        if not assessments:
            return EvidenceDecision(False, 0.0, 0.0, False, [], ["no_usable_evidence"])

        best = max(a.quality for a in assessments)
        diversity = min(1.0, len({self._registrable_domain(a.url) for a in assessments}) / 2.0)
        confidence = 0.55 * best + 0.20 * agreement + 0.15 * diversity + 0.10 * min(1.0, len(assessments) / 3.0)
        if contradiction:
            confidence *= 0.65
        confidence = round(min(0.99, confidence), 3)
        sufficient = len(assessments) >= 1 and confidence >= 0.70 and not contradiction
        reasons = ["usable_evidence"]
        if len(assessments) >= 2:
            reasons.append("multiple_sources")
        if agreement >= 0.75:
            reasons.append("cross_source_agreement")
        if contradiction:
            reasons.append("contradiction_detected")
        if sufficient:
            reasons.append("evidence_gate_passed")
        else:
            reasons.append("evidence_gate_not_passed")
        return EvidenceDecision(sufficient, confidence, agreement, contradiction, assessments, reasons)

    @classmethod
    def _source_reliability(cls, url: str) -> float:
        host = cls._registrable_domain(url)
        if host in cls.TRUSTED_DOMAINS:
            return cls.TRUSTED_DOMAINS[host]
        if any(marker in host for marker in cls.LOW_TRUST_MARKERS):
            return 0.55
        return 0.72 if host else 0.25

    @staticmethod
    def _registrable_domain(url: str) -> str:
        host = urlparse(url).netloc.lower().split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host

    @staticmethod
    def _freshness(query: str, content: str) -> float:
        q = query.lower()
        if not any(x in q for x in ("latest", "current", "hoy", "actual", "últim", "recent", "2026", "ahora")):
            return 0.75
        return 0.90 if re.search(r"\b20(2[5-9]|3\d)\b", content) else 0.55

    @staticmethod
    def _directness(query: str, content: str) -> float:
        tokens = {t for t in re.findall(r"[a-záéíóúñ0-9]{4,}", query.lower())}
        if not tokens:
            return 0.5
        body = content.lower()
        hits = sum(1 for token in tokens if token in body)
        return min(1.0, 0.35 + 0.65 * (hits / len(tokens)))

    @classmethod
    def _cross_source_signal(cls, query: str, evidence: list[dict[str, Any]]) -> tuple[float, bool]:
        if len(evidence) < 2:
            return 0.65, False
        texts = [str(item.get("content") or "").lower() for item in evidence]
        shared = set(re.findall(r"[a-záéíóúñ0-9]{5,}", texts[0]))
        for text in texts[1:]:
            shared &= set(re.findall(r"[a-záéíóúñ0-9]{5,}", text))
        agreement = min(1.0, 0.45 + 0.55 * min(1.0, len(shared) / 20.0))
        contradiction = any(any(marker in text for marker in cls.CONTRADICTION_MARKERS) for text in texts)
        return round(agreement, 3), contradiction
