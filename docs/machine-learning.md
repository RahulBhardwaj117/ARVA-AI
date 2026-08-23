# Machine learning

`forecast_series` is a real adaptive baseline pipeline:

| Available history | Model |
| --- | --- |
| Fewer than 6 values | Last-value baseline |
| 6–23 values | Linear regression |
| 24 or more values | Random forest regressor |

Features are the last observation, rolling mean, rolling standard deviation,
and time index. The pipeline holds out recent observations, calculates mean
absolute error, forecasts recursively to the requested horizon, and returns a
bounded interval and confidence.

Forecasts persist task, horizon, model name, prediction, bounds, confidence,
history size, and MAE. The model registry persists task, algorithm, version,
status, metrics, and feature contract.

This baseline design is deliberate: it remains useful under sparse demo data,
promotes to a nonlinear estimator when enough history exists, and exposes its
fallback instead of presenting unsupported confidence. Production extensions
can add artifact storage, walk-forward evaluation, drift thresholds, scheduled
retraining, and challenger promotion behind the same contract.

