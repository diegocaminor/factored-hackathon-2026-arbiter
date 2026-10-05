
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from propensity.catboost_modeling import prepare_catboost_frame
from propensity.features import add_propensity_interactions


ACTION_CHANNELS = ["Email", "SMS", "Push"]


def _first_existing(columns: Iterable[str], candidates: list[str]) -> str | None:
    columns = set(columns)
    for c in candidates:
        if c in columns:
            return c
    return None


def _mode_or_na(s: pd.Series):
    s = s.dropna()
    if s.empty:
        return "<NA>"
    m = s.mode()
    return m.iloc[0] if not m.empty else s.iloc[0]


def build_action_catalog(history_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a leakage-safe action catalog from historical PRE-TEST data only.
    One row represents a candidate country x product x channel action profile.
    """
    df = history_df.copy()
    df = df[df["send_channel"].isin(ACTION_CHANNELS)].copy()

    group_cols = ["country", "promoted_product", "send_channel"]

    # Expected value of a successful conversion. Prefer values observed on actual conversions.
    converted = df[df["had_conversion"].astype(int) == 1].copy()
    conv_value = (
        converted.groupby(group_cols, dropna=False)["conversion_value"]
        .median()
        .rename("estimated_conversion_value")
        .reset_index()
    )

    # Contact cost is paid per send, so use all historical sends.
    contact_cost = (
        df.groupby(group_cols, dropna=False)["send_cost"]
        .median()
        .rename("estimated_send_cost")
        .reset_index()
    )

    # Campaign/context values needed by the propensity model.
    mode_cols = [
        c for c in [
            "campaign_type",
            "campaign_objective",
            "target_segment",
            "target_country",
        ] if c in df.columns
    ]
    numeric_cols = [
        c for c in [
            "expected_conversion_rate",
            "send_hour",
            "send_day_of_week",
            "send_month",
            "is_weekend",
        ] if c in df.columns
    ]

    agg = {}
    for c in mode_cols:
        agg[c] = _mode_or_na
    for c in numeric_cols:
        agg[c] = "median"

    context = (
        df.groupby(group_cols, dropna=False)
        .agg(agg)
        .reset_index()
        if agg else df[group_cols].drop_duplicates().copy()
    )

    # Historical support is useful for auditability / minimum-evidence gating.
    support = (
        df.groupby(group_cols, dropna=False)
        .agg(
            historical_sends=("had_conversion", "size"),
            historical_conversions=("had_conversion", "sum"),
            historical_conversion_rate=("had_conversion", "mean"),
        )
        .reset_index()
    )

    catalog = context.merge(contact_cost, on=group_cols, how="left")
    catalog = catalog.merge(conv_value, on=group_cols, how="left")
    catalog = catalog.merge(support, on=group_cols, how="left")

    # Fallback conversion values if a very sparse action has no historical conversion.
    country_product_fallback = (
        converted.groupby(["country", "promoted_product"], dropna=False)["conversion_value"]
        .median()
        .rename("cp_conversion_value")
        .reset_index()
    )
    country_fallback = (
        converted.groupby(["country"], dropna=False)["conversion_value"]
        .median()
        .rename("country_conversion_value")
        .reset_index()
    )
    global_fallback = float(converted["conversion_value"].median()) if not converted.empty else 0.0

    catalog = catalog.merge(country_product_fallback, on=["country", "promoted_product"], how="left")
    catalog = catalog.merge(country_fallback, on=["country"], how="left")
    catalog["estimated_conversion_value"] = (
        catalog["estimated_conversion_value"]
        .fillna(catalog["cp_conversion_value"])
        .fillna(catalog["country_conversion_value"])
        .fillna(global_fallback)
    )
    catalog = catalog.drop(columns=["cp_conversion_value", "country_conversion_value"])

    return catalog.sort_values(group_cols).reset_index(drop=True)


def build_customer_snapshot(history_df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep the latest known PRE-TEST row per customer as the profile/context snapshot.
    """
    df = history_df.copy()
    customer_col = _first_existing(df.columns, ["customer_id", "client_id", "user_id"])
    if customer_col is None:
        raise ValueError("Could not find a customer identifier column.")

    date_col = _first_existing(
        df.columns,
        ["send_date", "send_datetime", "sent_at", "send_timestamp", "date"],
    )
    if date_col is not None:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col)
    else:
        df = df.reset_index(drop=False).sort_values("index")

    snapshot = df.groupby(customer_col, as_index=False).tail(1).copy()
    return snapshot.reset_index(drop=True)


@dataclass
class NBAResult:
    customer_id: object
    decision: str
    promoted_product: str | None
    send_channel: str | None
    propensity_raw: float | None
    expected_conversion_value: float | None
    estimated_send_cost: float | None
    expected_value: float | None
    historical_support: int | None


def score_customer_actions(
    customer_row: pd.Series,
    action_catalog: pd.DataFrame,
    model,
    model_features: list[str],
    categorical_features: list[str],
    min_historical_sends: int = 100,
) -> pd.DataFrame:
    """
    Score all supported product x channel actions for one customer.
    The catalog must come from PRE-TEST history.
    """
    country = customer_row["country"]
    candidates = action_catalog[
        (action_catalog["country"] == country)
        & (action_catalog["historical_sends"] >= min_historical_sends)
    ].copy()

    if candidates.empty:
        return candidates

    rows = []
    for _, action in candidates.iterrows():
        row = customer_row.copy()

        # Action variables.
        row["promoted_product"] = action["promoted_product"]
        row["send_channel"] = action["send_channel"]

        # Campaign/context variables learned from pre-test history.
        for c in [
            "campaign_type",
            "campaign_objective",
            "target_segment",
            "target_country",
            "expected_conversion_rate",
            "send_hour",
            "send_day_of_week",
            "send_month",
            "is_weekend",
        ]:
            if c in row.index and c in action.index and pd.notna(action[c]):
                row[c] = action[c]

        rows.append(row)

    X = pd.DataFrame(rows)
    X = add_propensity_interactions(X)
    X_model = X[model_features].copy()
    X_model = prepare_catboost_frame(X_model, categorical_features)

    probs = model.predict_proba(X_model)[:, 1]

    scored = candidates.reset_index(drop=True).copy()
    scored["propensity_raw"] = probs
    scored["expected_value"] = (
        scored["propensity_raw"] * scored["estimated_conversion_value"]
        - scored["estimated_send_cost"]
    )
    scored = scored.sort_values(
        ["expected_value", "propensity_raw"],
        ascending=[False, False],
    ).reset_index(drop=True)
    scored["rank"] = np.arange(1, len(scored) + 1)
    return scored


def recommend_next_best_action(
    customer_row: pd.Series,
    action_catalog: pd.DataFrame,
    model,
    model_features: list[str],
    categorical_features: list[str],
    min_historical_sends: int = 100,
) -> tuple[NBAResult, pd.DataFrame]:
    customer_col = _first_existing(customer_row.index, ["customer_id", "client_id", "user_id"])
    customer_id = customer_row[customer_col] if customer_col else None

    if "accepts_marketing" in customer_row.index:
        value = str(customer_row["accepts_marketing"]).strip().lower()
        if value in {"false", "0", "no", "n"}:
            return (
                NBAResult(customer_id, "NO_ACTION_CONSENT", None, None, None, None, None, None, None),
                pd.DataFrame(),
            )

    scored = score_customer_actions(
        customer_row=customer_row,
        action_catalog=action_catalog,
        model=model,
        model_features=model_features,
        categorical_features=categorical_features,
        min_historical_sends=min_historical_sends,
    )

    if scored.empty:
        return (
            NBAResult(customer_id, "NO_ACTION_NO_SUPPORTED_CANDIDATES", None, None, None, None, None, None, None),
            scored,
        )

    best = scored.iloc[0]
    if float(best["expected_value"]) <= 0:
        return (
            NBAResult(
                customer_id, "NO_ACTION_NEGATIVE_VALUE",
                str(best["promoted_product"]), str(best["send_channel"]),
                float(best["propensity_raw"]), float(best["estimated_conversion_value"]),
                float(best["estimated_send_cost"]), float(best["expected_value"]),
                int(best["historical_sends"]),
            ),
            scored,
        )

    return (
        NBAResult(
            customer_id, "ACTION",
            str(best["promoted_product"]), str(best["send_channel"]),
            float(best["propensity_raw"]), float(best["estimated_conversion_value"]),
            float(best["estimated_send_cost"]), float(best["expected_value"]),
            int(best["historical_sends"]),
        ),
        scored,
    )
