from pathlib import Path

from app.nba.settings import ArtifactPaths, resolve_artifact_paths


def test_defaults_to_local_artifacts_directory():
    paths = resolve_artifact_paths({})

    assert paths.root == Path("artifacts/propensity")
    assert paths.model == Path(
        "artifacts/propensity/final_evaluation/catboost_20261004_222052/model.joblib"
    )
    assert paths.action_catalog == Path("artifacts/propensity/nba/action_catalog_pretest.parquet")
    assert paths.customer_snapshot == Path(
        "artifacts/propensity/nba/customer_snapshot_pretest.parquet"
    )
    assert paths.metadata == Path("artifacts/propensity/nba/nba_metadata.json")


def test_empty_variable_falls_back_to_default():
    assert resolve_artifact_paths({"ARTIFACTS_DIR": ""}).root == Path("artifacts/propensity")


def test_artifacts_dir_overrides_root(tmp_path):
    paths = resolve_artifact_paths({"ARTIFACTS_DIR": str(tmp_path)})

    assert paths == ArtifactPaths.from_root(tmp_path)
    assert paths.metadata == tmp_path / "nba" / "nba_metadata.json"
