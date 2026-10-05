from __future__ import annotations

from pathlib import Path
import json
import joblib
import pandas as pd


def save_model_and_metadata(
    model,
    artifact_dir: str | Path,
    metadata: dict,
    model_filename: str = "propensity_logistic_pipeline.joblib",
    metadata_filename: str = "propensity_model_metadata.json",
):
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifact_dir / model_filename
    metadata_path = artifact_dir / metadata_filename

    joblib.dump(model, model_path)
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    return model_path, metadata_path


def build_scored_test(
    test_df: pd.DataFrame,
    probabilities,
    target: str,
) -> pd.DataFrame:
    scored = test_df[[
        "customer_id",
        "campaign_id",
        "send_date",
        "country",
        "promoted_product",
        "send_channel",
        target,
        "send_cost",
        "conversion_value",
    ]].copy()

    scored["predicted_conversion_probability"] = probabilities
    return scored


def save_scored_test(
    scored_test: pd.DataFrame,
    artifact_dir: str | Path,
    filename: str = "propensity_scored_test.parquet",
):
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    path = artifact_dir / filename
    scored_test.to_parquet(path, index=False)
    return path
