import pytest
from fastapi.testclient import TestClient

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
        assert app.state.nba_service is service
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
