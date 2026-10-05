from pathlib import Path

RANDOM_STATE = 42
TARGET = "had_conversion"

PROJECT_DIR = Path("/content/drive/MyDrive/03 Projects/Factored Hackathon")
DATASET_PATH = PROJECT_DIR / "data/processed/decision_dataset_base.parquet"
ARTIFACT_DIR = PROJECT_DIR / "artifacts/propensity"

NUMERIC_FEATURES = [
    "credit_score",
    "estimated_monthly_income",
    "expected_conversion_rate",
    "customer_age",
    "customer_tenure_days",
    "send_hour",
    "send_day_of_week",
    "send_month",
    "is_weekend",
]

CATEGORICAL_FEATURES = [
    "country",
    "gender",
    "segment",
    "marital_status",
    "education_level",
    "customer_status",
    "accepts_marketing",
    "campaign_type",
    "campaign_objective",
    "promoted_product",
    "target_segment",
    "target_country",
    "send_channel",
]

MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
