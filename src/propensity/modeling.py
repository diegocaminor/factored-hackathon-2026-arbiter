from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class LogisticConfig:
    name: str
    C: float = 1.0
    class_weight: Optional[str] = "balanced"
    max_iter: int = 500
    solver: str = "saga"
    min_frequency: Optional[int] = 10
    random_state: int = 42
    verbose: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def build_preprocessor(
    numeric_features: list[str],
    categorical_features: list[str],
    min_frequency: Optional[int] = 10,
) -> ColumnTransformer:
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                min_frequency=min_frequency,
            ),
        ),
    ])

    return ColumnTransformer([
        ("num", numeric_pipeline, numeric_features),
        ("cat", categorical_pipeline, categorical_features),
    ])


def build_logistic_pipeline(
    numeric_features: list[str],
    categorical_features: list[str],
    config: LogisticConfig,
) -> Pipeline:
    preprocessor = build_preprocessor(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        min_frequency=config.min_frequency,
    )

    model = LogisticRegression(
        C=config.C,
        max_iter=config.max_iter,
        class_weight=config.class_weight,
        solver=config.solver,
        n_jobs=-1,
        random_state=config.random_state,
        verbose=config.verbose,
    )

    return Pipeline([
        ("preprocess", preprocessor),
        ("model", model),
    ])


def train_logistic(
    X_train,
    y_train,
    numeric_features: list[str],
    categorical_features: list[str],
    config: LogisticConfig,
) -> Pipeline:
    pipeline = build_logistic_pipeline(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        config=config,
    )
    pipeline.fit(X_train, y_train)
    return pipeline
