from backend.app.core.task_artifacts import ArtifactContract, TaskArtifactRuntime


def test_task_tracks_steps_and_artifacts():
    runtime = TaskArtifactRuntime(max_tasks=2)
    task = runtime.create("t1", "research and create a report", "research")
    task.set_state("running", 25)
    task.add_step("research", "running")
    task.add_artifact(ArtifactContract("a1", "document", "Research report", mime_type="application/pdf"))

    payload = task.as_dict()
    assert payload["state"] == "running"
    assert payload["progress"] == 25
    assert payload["steps"][0]["name"] == "research"
    assert payload["artifacts"][0]["kind"] == "document"


def test_runtime_is_bounded():
    runtime = TaskArtifactRuntime(max_tasks=1)
    runtime.create("t1", "one")
    runtime.create("t2", "two")
    assert runtime.get("t1") is None
    assert runtime.get("t2") is not None
