from app.workspace_api import create_artifact

import asyncio
import pytest


def test_workspace_artifact_rejects_empty_content():
    with pytest.raises(Exception) as exc:
        asyncio.run(create_artifact("missing-workspace", {"artifact_type": "document", "content": ""}))
    assert getattr(exc.value, "status_code", None) == 404


def test_artifact_pipeline_accepts_supported_content():
    from app.core.artifact_pipeline import validate_artifact
    result = validate_artifact("document", {"content": "Bitey"})
    assert result["valid"] is True
    assert result["artifact_type"] == "document"
