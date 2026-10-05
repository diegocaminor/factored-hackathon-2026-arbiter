import pytest

from app.nba.loader import ArtifactLoadError, load_artifacts
from tests.nba.fakes import write_artifact_files as write_artifacts


def test_loads_valid_bundle(tmp_path):
    artifacts = load_artifacts(write_artifacts(tmp_path))

    assert artifacts.model == {"stub": "model"}
    assert len(artifacts.action_catalog) == 1
    assert artifacts.customer_id_column == "customer_id"
    assert dict(artifacts.customer_positions) == {"CLI-A": 0, "CLI-B": 1}
    assert artifacts.model_features == ("country", "segment")
    assert artifacts.categorical_features == ("country",)
    assert artifacts.min_historical_sends == 100


def test_bundle_is_immutable(tmp_path):
    artifacts = load_artifacts(write_artifacts(tmp_path))

    with pytest.raises(AttributeError):
        artifacts.model = None
    with pytest.raises(TypeError):
        artifacts.customer_positions["CLI-C"] = 2


def test_missing_snapshot_names_path(tmp_path):
    paths = write_artifacts(tmp_path)
    paths.customer_snapshot.unlink()

    with pytest.raises(ArtifactLoadError, match="customer_snapshot_pretest.parquet"):
        load_artifacts(paths)


def test_metadata_missing_keys(tmp_path):
    paths = write_artifacts(tmp_path, metadata={"model_features": ["country"]})

    with pytest.raises(ArtifactLoadError, match="categorical_features, min_historical_sends"):
        load_artifacts(paths)


def test_unreadable_artifact_names_path(tmp_path):
    paths = write_artifacts(tmp_path)
    paths.action_catalog.write_bytes(b"not a parquet file")

    with pytest.raises(ArtifactLoadError, match="action_catalog_pretest.parquet"):
        load_artifacts(paths)
