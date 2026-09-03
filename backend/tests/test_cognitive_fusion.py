from app.core.cognitive_fusion import CognitiveFusion, ContradictionEngine, EvidenceItem, TaskDecompositionEngine


def test_detects_explicit_negation_conflict():
    engine = ContradictionEngine()
    conflicts = engine.compare([
        EvidenceItem("memory", "service is enabled"),
        EvidenceItem("official", "service is not enabled"),
    ])
    assert len(conflicts) == 1
    assert conflicts[0].severity == "high"


def test_fusion_marks_verification_when_conflicted():
    fusion = CognitiveFusion()
    result = fusion.prepare(
        "verifica esta arquitectura y compara las fuentes",
        brain_state={"complexity": 0.8, "verification_required": True},
        sources={
            "memory": [{"content": "service is enabled", "confidence": 0.7}],
            "official": [{"content": "service is not enabled", "confidence": 0.95}],
        },
    )
    assert result["knowledge_fusion"]["contradiction_count"] == 1
    assert result["knowledge_fusion"]["needs_verification"] is True
    assert result["task_plan"]["planned"] is True


def test_simple_task_stays_bounded():
    plan = TaskDecompositionEngine().decompose("hola", {"complexity": 0.2})
    assert plan["planned"] is False
    assert plan["step_count"] == 1
