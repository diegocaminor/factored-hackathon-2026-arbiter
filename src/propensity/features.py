from __future__ import annotations

import pandas as pd


INTERACTION_FEATURES = [
    "country_product_channel",
    "segment_product",
    "campaign_objective_product",
]


def add_propensity_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """Create pre-send categorical interaction features without using outcomes."""
    out = df.copy()

    out["country_product_channel"] = (
        out["country"].astype("string").fillna("<NA>")
        + "__"
        + out["promoted_product"].astype("string").fillna("<NA>")
        + "__"
        + out["send_channel"].astype("string").fillna("<NA>")
    )

    out["segment_product"] = (
        out["segment"].astype("string").fillna("<NA>")
        + "__"
        + out["promoted_product"].astype("string").fillna("<NA>")
    )

    out["campaign_objective_product"] = (
        out["campaign_objective"].astype("string").fillna("<NA>")
        + "__"
        + out["promoted_product"].astype("string").fillna("<NA>")
    )

    return out
