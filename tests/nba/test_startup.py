import json

import pytest
from fastapi.testclient import TestClient

from app.agent.service import AgentService
from app.execution.service import ExecutionService
from app.main import app
from app.nba.loader import ArtifactLoadError
from app.nba.service import NBAService
from tests.nba.fakes import write_artifact_files


def test_startup_fails_when_artifacts_are_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))

    with pytest.raises(ArtifactLoadError, match=str(tmp_path)):
        with TestClient(app):
            pass


def test_startup_loads_service_once_and_health_stays_liveness(tmp_path, monkeypatch):
    write_artifact_files(tmp_path)
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))

    with TestClient(app) as client:
        service = app.state.nba_service
        response = client.get("/health")
        client.get("/health")

        assert isinstance(service, NBAService)
        assert isinstance(app.state.execution_service, ExecutionService)
        assert app.state.execution_service._nba is service
        assert isinstance(app.state.agent_service, AgentService)
        assert app.state.agent_service._nba is service
        assert app.state.nba_service is service
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_startup_fails_on_invalid_min_historical_sends(tmp_path, monkeypatch):
    paths = write_artifact_files(tmp_path)
    metadata = json.loads(paths.metadata.read_text())
    paths.metadata.write_text(json.dumps({**metadata, "min_historical_sends": 0}))
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))

    with pytest.raises(ArtifactLoadError, match="min_historical_sends"):
        with TestClient(app):
            pass
