from app.core.workspace_runtime import WorkspaceRuntime


def test_workspace_plan_can_produce_multiple_artifacts():
    plan = WorkspaceRuntime().plan(
        "Investiga el mercado de IA y prepara informe + presentación + Excel",
        mode="research",
        domain="research",
    )
    assert plan.task.state == "queued"
    assert {artifact.kind for artifact in plan.task.artifacts} >= {"research", "documents", "slides", "sheets"}
    assert plan.task.progress == 15


def test_workspace_plan_is_bounded():
    runtime = WorkspaceRuntime(max_capabilities=3, max_artifacts=3)
    plan = runtime.plan("crea informe, ppt, excel, imagen, video, website")
    assert len(plan.capabilities) <= 3
    assert len(plan.task.artifacts) <= 3
