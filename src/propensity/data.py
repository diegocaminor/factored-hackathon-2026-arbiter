from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass
class TemporalSplit:
    train_df: pd.DataFrame
    validation_df: pd.DataFrame
    test_df: pd.DataFrame
    train_cutoff: pd.Timestamp
    validation_cutoff: pd.Timestamp


def load_dataset(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Run notebook 03 first."
        )
    return pd.read_parquet(path)


def validate_columns(
    df: pd.DataFrame,
    model_features: list[str],
    target: str,
    date_column: str = "send_date",
) -> None:
    missing = [
        c for c in model_features + [target, date_column]
        if c not in df.columns
    ]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")


def temporal_split(
    df: pd.DataFrame,
    train_quantile: float = 0.70,
    validation_quantile: float = 0.85,
    date_column: str = "send_date",
) -> TemporalSplit:
    ordered = df.sort_values(date_column).reset_index(drop=True)

    train_cutoff = ordered[date_column].quantile(train_quantile)
    validation_cutoff = ordered[date_column].quantile(validation_quantile)

    train_df = ordered[ordered[date_column] <= train_cutoff].copy()
    validation_df = ordered[
        (ordered[date_column] > train_cutoff)
        & (ordered[date_column] <= validation_cutoff)
    ].copy()
    test_df = ordered[ordered[date_column] > validation_cutoff].copy()

    return TemporalSplit(
        train_df=train_df,
        validation_df=validation_df,
        test_df=test_df,
        train_cutoff=train_cutoff,
        validation_cutoff=validation_cutoff,
    )


def make_xy(
    df: pd.DataFrame,
    model_features: list[str],
    target: str,
):
    X = df[model_features]
    y = df[target].astype(int)
    return X, y
