"""Conversions from pandas/numpy values to JSON-safe Python values."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


def is_missing(value: Any) -> bool:
    return value is None or bool(pd.isna(value))


def optional_float(value: Any) -> float | None:
    if is_missing(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def optional_int(value: Any) -> int | None:
    return None if is_missing(value) else int(value)


def optional_str(value: Any) -> str | None:
    return None if is_missing(value) else str(value)
