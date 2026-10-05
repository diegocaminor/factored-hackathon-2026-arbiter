import json
from types import MappingProxyType

import joblib
import numpy as np
import pandas as pd

from app.nba.loader import NBAArtifacts
from app.nba.settings import ArtifactPaths

FEATURES = (
    "country",
    "segment",
    "campaign_objective",
    "promoted_product",
    "send_channel",
    "country_product_channel",
    "segment_product",
    "campaign_objective_product",
)

# Chile: six supported actions with distinct positive expected values (99, 89, ..., 49).
CHILE_PROBABILITIES = {
    ("Cuenta Ahorro", "Email"): 0.10,
    ("Cuenta Ahorro", "SMS"): 0.09,
    ("Seguro", "Email"): 0.08,
    ("Seguro", "SMS"): 0.07,
    ("Inversión", "Email"): 0.06,
    ("Inversión", "SMS"): 0.05,
}


class StubModel:
    """Deterministic predict_proba keyed by (product, channel); counts calls."""

    def __init__(self, probabilities, default=0.05):
        self.probabilities = probabilities
        self.default = default
        self.calls = 0

    def predict_proba(self, X):
        self.calls += 1
        positive = np.array(
            [
                self.probabilities.get((product, channel), self.default)
                for product, channel in zip(X["promoted_product"], X["send_channel"])
            ]
        )
        return np.column_stack([1 - positive, positive])


def build_catalog():
    rows = [
        {
            "country": "Chile",
            "promoted_product": product,
            "send_channel": channel,
            "campaign_objective": "Cross-sell",
            "estimated_conversion_value": 1000.0,
            "estimated_send_cost": 1.0,
            "historical_sends": 500,
        }
        for product, channel in CHILE_PROBABILITIES
    ]
    rows += [
        # México: supported but unprofitable.
        {
            "country": "México",
            "promoted_product": "Seguro",
            "send_channel": "SMS",
            "campaign_objective": "Cross-sell",
            "estimated_conversion_value": 10.0,
            "estimated_send_cost": 5.0,
            "historical_sends": 300,
        },
        # Perú: below the minimum historical support.
        {
            "country": "Perú",
            "promoted_product": "Seguro",
            "send_channel": "Email",
            "campaign_objective": "Cross-sell",
            "estimated_conversion_value": 1000.0,
            "estimated_send_cost": 1.0,
            "historical_sends": 10,
        },
        # Colombia: one valid action and one with a missing conversion value.
        {
            "country": "Colombia",
            "promoted_product": "Seguro",
            "send_channel": "Push",
            "campaign_objective": "Cross-sell",
            "estimated_conversion_value": 500.0,
            "estimated_send_cost": 1.0,
            "historical_sends": 200,
        },
        {
            "country": "Colombia",
            "promoted_product": "Inversión",
            "send_channel": "Push",
            "campaign_objective": "Cross-sell",
            "estimated_conversion_value": np.nan,
            "estimated_send_cost": 1.0,
            "historical_sends": 200,
        },
    ]
    return pd.DataFrame(rows)


def build_snapshot():
    customers = [
        ("CLI-ACTION", "Chile", True),
        ("CLI-CONSENT", "Chile", False),
        ("CLI-NEGATIVE", "México", True),
        ("CLI-UNSUPPORTED", "Perú", True),
        ("CLI-NAN", "Colombia", True),
    ]
    return pd.DataFrame(
        [
            {
                "customer_id": customer_id,
                "country": country,
                "accepts_marketing": consent,
                "segment": "Plus",
                "campaign_objective": "Retention",
                "promoted_product": "Cuenta Corriente",
                "send_channel": "Email",
            }
            for customer_id, country, consent in customers
        ]
    )


def build_artifacts(model):
    snapshot = build_snapshot()
    return NBAArtifacts(
        model=model,
        action_catalog=build_catalog(),
        customer_snapshot=snapshot,
        customer_id_column="customer_id",
        customer_positions=MappingProxyType(
            {cid: pos for pos, cid in enumerate(snapshot["customer_id"])}
        ),
        model_features=FEATURES,
        categorical_features=FEATURES,
        min_historical_sends=100,
    )


FILE_METADATA = {
    "model_features": ["country", "segment"],
    "categorical_features": ["country"],
    "min_historical_sends": 100,
}


def write_artifact_files(root, metadata=FILE_METADATA):
    """Write minimal, loadable artifact files under root."""
    paths = ArtifactPaths.from_root(root)
    for path in paths.required():
        path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"stub": "model"}, paths.model)
    pd.DataFrame({"country": ["Chile"], "historical_sends": [150]}).to_parquet(
        paths.action_catalog
    )
    pd.DataFrame({"customer_id": ["CLI-A", "CLI-B"], "country": ["Chile", "Perú"]}).to_parquet(
        paths.customer_snapshot
    )
    paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")
    return paths
