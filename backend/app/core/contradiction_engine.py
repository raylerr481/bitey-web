from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Any
@dataclass(frozen=True)
class ContradictionReport:
    contradiction_detected: bool; evidence_count: int; domains: list[str]; action: str; confidence: float; reasons: list[str]
    def as_dict(self)->dict[str,Any]: return asdict(self)
class ContradictionEngine:
    """Evidence consistency gate using similar numeric claim sentences."""
    NUMBERS=re.compile(r"[-+]?\d+(?:[.,]\d+)?")
    def inspect(self,evidence:list[dict[str,Any]]|None=None)->ContradictionReport:
        usable=[e for e in (evidence or []) if e.get("ok") and e.get("content")]
        if len(usable)<2: return ContradictionReport(False,len(usable),[],"search_more",0.45,["insufficient_independent_evidence"])
        claims:dict[str,set[str]]={}
        for item in usable:
            for sentence in re.split(r"(?<=[.!?])\s+",str(item.get("content") or "")):
                nums=self.NUMBERS.findall(sentence)
                if not nums: continue
                key=re.sub(r"[-+]?\d+(?:[.,]\d+)?","#",sentence.lower()); key=re.sub(r"\s+"," ",key).strip()
                for n in nums: claims.setdefault(key,set()).add(n.replace(",","."))
        contradiction=any(len(values)>1 for values in claims.values())
        return ContradictionReport(contradiction,len(usable),[],"search_more" if contradiction else "answer",0.78 if contradiction else min(0.92,0.55+0.08*len(usable)),["multiple_sources_available"]+(["similar_claims_have_conflicting_values"] if contradiction else []))
