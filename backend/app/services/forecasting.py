"""Deterministic forecasting pipeline with transparent fallbacks."""

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


@dataclass(frozen=True)
class ForecastResult:
    """One model forecast with an uncertainty interval."""

    prediction: float
    lower: float
    upper: float
    confidence: float
    model_name: str
    mae: float


def forecast_series(values: list[float], horizon: int = 5, seed: int = 42) -> ForecastResult:
    """Forecast a bounded numeric series using the strongest supported baseline.

    Random forest is used for longer histories, linear regression for short
    histories, and a last-value baseline when only a few measurements exist.
    """
    clean = np.asarray([float(value) for value in values if np.isfinite(value)], dtype=float)
    if clean.size == 0:
        clean = np.asarray([0.0])

    if clean.size < 6:
        prediction = float(clean[-1])
        spread = max(abs(prediction) * 0.2, 1.0)
        return ForecastResult(
            prediction=prediction,
            lower=max(0.0, prediction - spread),
            upper=prediction + spread,
            confidence=0.45,
            model_name="last_value",
            mae=spread,
        )

    window = min(6, max(3, clean.size // 4))
    features: list[list[float]] = []
    targets: list[float] = []
    for index in range(window, clean.size):
        segment = clean[index - window : index]
        features.append(
            [
                float(segment[-1]),
                float(segment.mean()),
                float(segment.std()),
                float(index),
            ]
        )
        targets.append(float(clean[index]))

    split = max(1, int(len(features) * 0.8))
    train_x = np.asarray(features[:split])
    train_y = np.asarray(targets[:split])
    test_x = np.asarray(features[split:] or features[-1:])
    test_y = np.asarray(targets[split:] or targets[-1:])

    if clean.size >= 24 and len(train_x) >= 8:
        model = RandomForestRegressor(
            n_estimators=60,
            max_depth=6,
            random_state=seed,
            n_jobs=1,
        )
        model_name = "random_forest"
    else:
        model = LinearRegression()
        model_name = "linear_regression"

    model.fit(train_x, train_y)
    validation = model.predict(test_x)
    mae = float(mean_absolute_error(test_y, validation))
    rolling = clean[-window:].copy()
    predicted = float(rolling[-1])
    for step in range(max(1, horizon)):
        next_features = np.asarray(
            [[float(rolling[-1]), float(rolling.mean()), float(rolling.std()), clean.size + step]]
        )
        predicted = max(0.0, float(model.predict(next_features)[0]))
        rolling = np.append(rolling[1:], predicted)

    spread = max(mae * 1.96, abs(predicted) * 0.08, 0.5)
    confidence = max(0.5, min(0.96, 1 - mae / max(abs(float(clean.mean())), 1.0)))
    return ForecastResult(
        prediction=predicted,
        lower=max(0.0, predicted - spread),
        upper=predicted + spread,
        confidence=confidence,
        model_name=model_name,
        mae=mae,
    )

