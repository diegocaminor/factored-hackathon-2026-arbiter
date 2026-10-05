from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
)


def positive_probabilities(model, X) -> np.ndarray:
    return model.predict_proba(X)[:, 1]


def evaluate_probabilities(
    y_true,
    probabilities,
    name: str | None = None,
) -> dict:
    pr_auc = average_precision_score(y_true, probabilities)
    roc_auc = roc_auc_score(y_true, probabilities)
    base_rate = float(np.mean(y_true))

    result = {
        "pr_auc": float(pr_auc),
        "roc_auc": float(roc_auc),
        "base_conversion_rate": base_rate,
    }

    if name:
        print(name)
        print(f"  PR-AUC / Average Precision: {pr_auc:.6f}")
        print(f"  ROC-AUC:                    {roc_auc:.6f}")
        print(f"  Base conversion rate:       {base_rate:.6f}")

    return result


def propensity_deciles(
    y_true,
    probabilities,
    n_bins: int = 10,
) -> pd.DataFrame:
    tmp = pd.DataFrame({
        "actual": np.asarray(y_true),
        "propensity": probabilities,
    })

    # Rank first so qcut always creates equal-sized bins even with tied scores.
    ranked = tmp["propensity"].rank(method="first")
    tmp["decile"] = pd.qcut(
        ranked,
        q=n_bins,
        labels=False,
    ) + 1

    result = (
        tmp.groupby("decile", observed=True)
        .agg(
            rows=("actual", "size"),
            conversions=("actual", "sum"),
            observed_conversion_rate=("actual", "mean"),
            avg_propensity=("propensity", "mean"),
        )
        .sort_index(ascending=False)
    )

    overall = tmp["actual"].mean()
    result["lift_vs_random"] = (
        result["observed_conversion_rate"] / overall
        if overall > 0
        else np.nan
    )
    return result


def best_f1_threshold(y_true, probabilities) -> dict:
    precision, recall, thresholds = precision_recall_curve(
        y_true,
        probabilities,
    )

    table = pd.DataFrame({
        "threshold": thresholds,
        "precision": precision[:-1],
        "recall": recall[:-1],
    })

    table["f1"] = (
        2
        * table["precision"]
        * table["recall"]
        / (
            table["precision"]
            + table["recall"]
            + 1e-12
        )
    )

    best_idx = table["f1"].idxmax()
    best = table.loc[best_idx]

    return {
        "threshold": float(best["threshold"]),
        "precision": float(best["precision"]),
        "recall": float(best["recall"]),
        "f1": float(best["f1"]),
        "table": table,
    }


def evaluate_model(model, X, y, name: str) -> dict:
    probabilities = positive_probabilities(model, X)
    metrics = evaluate_probabilities(y, probabilities, name=name)
    threshold = best_f1_threshold(y, probabilities)
    deciles = propensity_deciles(y, probabilities)

    return {
        **metrics,
        "best_f1_threshold": threshold["threshold"],
        "precision_at_best_f1": threshold["precision"],
        "recall_at_best_f1": threshold["recall"],
        "best_f1": threshold["f1"],
        "threshold_table": threshold["table"],
        "deciles": deciles,
        "probabilities": probabilities,
    }
