from app.api.workspace import registry, runtime, tasks


def test_workspace_capabilities_are_free_first():
    assert registry.all()
    assert all(item.free_local for item in registry.all())


def test_workspace_task_plan_creates_multiple_artifacts():
    plan = runtime.plan(
        "Investiga IA y prepara un informe, presentación y hoja de cálculo",
        mode="research",
    )
    kinds = {artifact.kind for artifact in plan.task.artifacts}
    assert {"documents", "slides", "sheets"}.issubset(kinds)
    assert plan.task.state == "queued"
    assert plan.task.progress == 15


def test_task_registry_contract_is_bounded():
    task = runtime.plan("Crea un documento sobre Bitey").task
    tasks._tasks[task.task_id] = task
    assert tasks.get(task.task_id) is task
