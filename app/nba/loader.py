from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeVar

import joblib
import pandas as pd

from app.nba.settings import ArtifactPaths

# Same identifier candidates the NBA engine resolves, in the same order.
CUSTOMER_ID_COLUMNS = ("customer_id", "client_id", "user_id")
REQUIRED_METADATA_KEYS = ("model_features", "categorical_features", "min_historical_sends")

T = TypeVar("T")


class ArtifactLoadError(RuntimeError):
    """A required NBA artifact is missing or cannot be loaded."""


@dataclass(frozen=True)
class NBAArtifacts:
    """Frozen model, pre-test data, and engine parameters, loaded once at startup."""

    model: Any
    action_catalog: pd.DataFrame
    customer_snapshot: pd.DataFrame
    customer_id_column: str
    customer_positions: Mapping[str, int]
    model_features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    min_historical_sends: int


def load_artifacts(paths: ArtifactPaths) -> NBAArtifacts:
    for path in paths.required():
        if not path.is_file():
            raise ArtifactLoadError(f"Required NBA artifact not found: {path}")

    metadata = _load(paths.metadata, lambda p: json.loads(p.read_text(encoding="utf-8")))
    missing_keys = [key for key in REQUIRED_METADATA_KEYS if key not in metadata]
    if missing_keys:
        raise ArtifactLoadError(
            f"NBA metadata {paths.metadata} is missing keys: {', '.join(missing_keys)}"
        )

    model = _load(paths.model, joblib.load)
    action_catalog = _load(paths.action_catalog, pd.read_parquet)
    customer_snapshot = _load(paths.customer_snapshot, pd.read_parquet)

    id_column = next((c for c in CUSTOMER_ID_COLUMNS if c in customer_snapshot.columns), None)
    if id_column is None:
        raise ArtifactLoadError(
            f"Customer snapshot {paths.customer_snapshot} has no customer identifier column"
        )
    positions = {str(cid): pos for pos, cid in enumerate(customer_snapshot[id_column])}

    return NBAArtifacts(
        model=model,
        action_catalog=action_catalog,
        customer_snapshot=customer_snapshot,
        customer_id_column=id_column,
        customer_positions=MappingProxyType(positions),
        model_features=tuple(metadata["model_features"]),
        categorical_features=tuple(metadata["categorical_features"]),
        min_historical_sends=int(metadata["min_historical_sends"]),
    )


def _load(path: Path, reader: Callable[[Path], T]) -> T:
    try:
        return reader(path)
    except Exception as exc:
        raise ArtifactLoadError(f"Failed to load NBA artifact {path}: {exc}") from exc
