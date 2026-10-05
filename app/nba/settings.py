from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ARTIFACTS_DIR_ENV = "ARTIFACTS_DIR"
DEFAULT_ARTIFACTS_DIR = Path("artifacts/propensity")

MODEL_PATH = Path("final_evaluation/catboost_20261004_222052/model.joblib")
ACTION_CATALOG_PATH = Path("nba/action_catalog_pretest.parquet")
CUSTOMER_SNAPSHOT_PATH = Path("nba/customer_snapshot_pretest.parquet")
METADATA_PATH = Path("nba/nba_metadata.json")


@dataclass(frozen=True)
class ArtifactPaths:
    """Locations of the frozen NBA artifacts under one artifacts directory."""

    root: Path
    model: Path
    action_catalog: Path
    customer_snapshot: Path
    metadata: Path

    @classmethod
    def from_root(cls, root: Path) -> ArtifactPaths:
        return cls(
            root=root,
            model=root / MODEL_PATH,
            action_catalog=root / ACTION_CATALOG_PATH,
            customer_snapshot=root / CUSTOMER_SNAPSHOT_PATH,
            metadata=root / METADATA_PATH,
        )

    def required(self) -> tuple[Path, ...]:
        return (self.model, self.action_catalog, self.customer_snapshot, self.metadata)


def resolve_artifact_paths(environ: Mapping[str, str] | None = None) -> ArtifactPaths:
    """Resolve artifact paths from ARTIFACTS_DIR, defaulting to ./artifacts/propensity."""
    env = os.environ if environ is None else environ
    root = Path(env.get(ARTIFACTS_DIR_ENV) or DEFAULT_ARTIFACTS_DIR)
    return ArtifactPaths.from_root(root)
