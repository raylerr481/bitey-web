from app.core.workspace_orchestrator import WorkspaceOrchestrator


def test_detects_multiple_requested_deliverables():
    orchestrator = WorkspaceOrchestrator()
    plan = orchestrator.plan(
        "Investiga el mercado de IA y prepara un informe, una presentación y una hoja de Excel"
    )
    assert [item.artifact_type for item in plan] == ["document", "presentation", "spreadsheet"]


def test_planner_is_bounded():
    orchestrator = WorkspaceOrchestrator()
    prompt = "document presentation spreadsheet code " * 20
    assert len(orchestrator.plan(prompt)) <= orchestrator.MAX_DELIVERABLES
