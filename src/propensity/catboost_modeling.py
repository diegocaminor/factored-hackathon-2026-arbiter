from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd
from catboost import CatBoostClassifier


@dataclass(frozen=True)
class CatBoostConfig:
    name: str
    iterations: int = 500
    depth: int = 7
    learning_rate: float = 0.05
    l2_leaf_reg: float = 5.0
    random_state: int = 42
    auto_class_weights: str | None = None
    early_stopping_rounds: int = 75

    def as_dict(self) -> dict:
        return asdict(self)


def prepare_catboost_frame(
    X: pd.DataFrame,
    categorical_features: list[str],
) -> pd.DataFrame:
    """CatBoost expects categorical columns to have explicit string values."""
    out = X.copy()
    for col in categorical_features:
        out[col] = out[col].astype("string").fillna("<NA>").astype(str)
    return out


def train_catboost(
    X_train: pd.DataFrame,
    y_train,
    X_val: pd.DataFrame,
    y_val,
    categorical_features: list[str],
    config: CatBoostConfig,
) -> CatBoostClassifier:
    X_train_cb = prepare_catboost_frame(X_train, categorical_features)
    X_val_cb = prepare_catboost_frame(X_val, categorical_features)

    model = CatBoostClassifier(
        iterations=config.iterations,
        depth=config.depth,
        learning_rate=config.learning_rate,
        l2_leaf_reg=config.l2_leaf_reg,
        loss_function="Logloss",
        eval_metric="AUC",
        random_seed=config.random_state,
        auto_class_weights=config.auto_class_weights,
        verbose=50,
        allow_writing_files=False,
        thread_count=-1,
    )

    model.fit(
        X_train_cb,
        y_train,
        cat_features=categorical_features,
        eval_set=(X_val_cb, y_val),
        use_best_model=True,
        early_stopping_rounds=config.early_stopping_rounds,
    )
    return model
