from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable


@dataclass
class AnomalyResult:
    metric: str
    current_value: float
    baseline_mean: float
    baseline_stddev: float
    z_score: float
    is_anomaly: bool
    severity: str


class StatisticalAnomalyDetector:
    """
    Statistical anomaly detector based on historical mean and
    population standard deviation.

    Severity levels:

        NORMAL      -> |z| < 2
        WARNING     -> 2 <= |z| < 3
        CRITICAL    -> |z| >= 3

    The detector requires a minimum amount of historical data
    before producing a meaningful result.
    """

    DEFAULT_WARNING_THRESHOLD = 2.0
    DEFAULT_CRITICAL_THRESHOLD = 3.0
    DEFAULT_MIN_HISTORY = 3

    def __init__(
        self,
        warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
        critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
        min_history: int = DEFAULT_MIN_HISTORY,
    ):
        if warning_threshold <= 0:
            raise ValueError(
                "warning_threshold must be greater than zero."
            )

        if critical_threshold <= warning_threshold:
            raise ValueError(
                "critical_threshold must be greater than "
                "warning_threshold."
            )

        if min_history < 2:
            raise ValueError(
                "min_history must be at least 2."
            )

        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.min_history = min_history

    def detect(
        self,
        metric: str,
        current_value: float,
        historical_values: Iterable[float],
    ) -> AnomalyResult:
        """
        Compare the current metric value against historical values.
        """

        if not metric or not metric.strip():
            raise ValueError(
                "metric must be a non-empty string."
            )

        try:
            current = float(current_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "current_value must be numeric."
            ) from exc

        history = []

        for value in historical_values:
            try:
                history.append(float(value))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "historical_values must contain only numeric values."
                ) from exc

        if len(history) < self.min_history:
            raise ValueError(
                f"At least {self.min_history} historical values "
                "are required."
            )

        baseline_mean = mean(history)
        baseline_stddev = pstdev(history)

        # If all historical values are identical, the standard
        # deviation is zero. In that case, any deviation from
        # the baseline is treated as a strong anomaly.
        if baseline_stddev == 0:
            if current == baseline_mean:
                z_score = 0.0
                severity = "NORMAL"
                is_anomaly = False
            else:
                z_score = float("inf")
                severity = "CRITICAL"
                is_anomaly = True

            return AnomalyResult(
                metric=metric,
                current_value=current,
                baseline_mean=baseline_mean,
                baseline_stddev=baseline_stddev,
                z_score=z_score,
                is_anomaly=is_anomaly,
                severity=severity,
            )

        z_score = (
            (current - baseline_mean)
            / baseline_stddev
        )

        absolute_z = abs(z_score)

        if absolute_z >= self.critical_threshold:
            severity = "CRITICAL"
            is_anomaly = True

        elif absolute_z >= self.warning_threshold:
            severity = "WARNING"
            is_anomaly = True

        else:
            severity = "NORMAL"
            is_anomaly = False

        return AnomalyResult(
            metric=metric,
            current_value=current,
            baseline_mean=baseline_mean,
            baseline_stddev=baseline_stddev,
            z_score=z_score,
            is_anomaly=is_anomaly,
            severity=severity,
        )


def run_tests() -> bool:
    print("FLOWMART STATISTICAL ANOMALY DETECTOR")
    print("=====================================")

    detector = StatisticalAnomalyDetector()

    # ---------------------------------------------------------
    # Test 1 — Normal value
    # ---------------------------------------------------------

    result = detector.detect(
        metric="daily_revenue",
        current_value=1010,
        historical_values=[
            1000,
            990,
            1015,
            1005,
            995,
        ],
    )

    assert result.is_anomaly is False
    assert result.severity == "NORMAL"

    print("[PASS] Test 1 — Normal value.")

    # ---------------------------------------------------------
    # Test 2 — Warning anomaly
    #
    # The previous version incorrectly used 1040 here.
    # That value is far beyond 3 standard deviations and is
    # correctly classified as CRITICAL.
    #
    # 1018 produces a z-score between 2 and 3.
    # ---------------------------------------------------------

    result = detector.detect(
        metric="daily_revenue",
        current_value=1018,
        historical_values=[
            1000,
            990,
            1010,
            1005,
            995,
        ],
    )

    assert result.is_anomaly is True
    assert result.severity == "WARNING"
    assert 2 <= abs(result.z_score) < 3

    print("[PASS] Test 2 — Warning anomaly.")

    # ---------------------------------------------------------
    # Test 3 — Critical anomaly
    # ---------------------------------------------------------

    result = detector.detect(
        metric="daily_revenue",
        current_value=1100,
        historical_values=[
            1000,
            990,
            1010,
            1005,
            995,
        ],
    )

    assert result.is_anomaly is True
    assert result.severity == "CRITICAL"
    assert abs(result.z_score) >= 3

    print("[PASS] Test 3 — Critical anomaly.")

    # ---------------------------------------------------------
    # Test 4 — Negative anomaly
    # ---------------------------------------------------------

    result = detector.detect(
        metric="daily_revenue",
        current_value=900,
        historical_values=[
            1000,
            990,
            1010,
            1005,
            995,
        ],
    )

    assert result.is_anomaly is True
    assert result.severity == "CRITICAL"

    print("[PASS] Test 4 — Negative anomaly detected.")

    # ---------------------------------------------------------
    # Test 5 — Stable baseline
    # ---------------------------------------------------------

    result = detector.detect(
        metric="order_count",
        current_value=100,
        historical_values=[
            100,
            100,
            100,
            100,
        ],
    )

    assert result.is_anomaly is False
    assert result.severity == "NORMAL"
    assert result.z_score == 0.0

    print("[PASS] Test 5 — Stable baseline.")

    # ---------------------------------------------------------
    # Test 6 — Stable baseline with deviation
    # ---------------------------------------------------------

    result = detector.detect(
        metric="order_count",
        current_value=150,
        historical_values=[
            100,
            100,
            100,
            100,
        ],
    )

    assert result.is_anomaly is True
    assert result.severity == "CRITICAL"
    assert result.z_score == float("inf")

    print("[PASS] Test 6 — Zero-standard-deviation anomaly.")

    # ---------------------------------------------------------
    # Test 7 — Insufficient history
    # ---------------------------------------------------------

    try:
        detector.detect(
            metric="daily_revenue",
            current_value=1000,
            historical_values=[
                990,
                1010,
            ],
        )

        raise AssertionError(
            "Expected insufficient-history error."
        )

    except ValueError as exc:
        assert "At least 3 historical values" in str(exc)

    print("[PASS] Test 7 — Insufficient history rejected.")

    # ---------------------------------------------------------
    # Test 8 — Invalid current value
    # ---------------------------------------------------------

    try:
        detector.detect(
            metric="daily_revenue",
            current_value="not-a-number",
            historical_values=[
                1000,
                990,
                1010,
            ],
        )

        raise AssertionError(
            "Expected invalid current value error."
        )

    except ValueError as exc:
        assert "current_value must be numeric" in str(exc)

    print("[PASS] Test 8 — Invalid current value rejected.")

    # ---------------------------------------------------------
    # Test 9 — Invalid historical value
    # ---------------------------------------------------------

    try:
        detector.detect(
            metric="daily_revenue",
            current_value=1000,
            historical_values=[
                1000,
                "bad-value",
                1010,
            ],
        )

        raise AssertionError(
            "Expected invalid historical value error."
        )

    except ValueError as exc:
        assert (
            "historical_values must contain only numeric values"
            in str(exc)
        )

    print("[PASS] Test 9 — Invalid historical value rejected.")

    # ---------------------------------------------------------
    # Test 10 — Invalid configuration
    # ---------------------------------------------------------

    try:
        StatisticalAnomalyDetector(
            warning_threshold=3.0,
            critical_threshold=2.0,
        )

        raise AssertionError(
            "Expected invalid threshold configuration."
        )

    except ValueError as exc:
        assert (
            "critical_threshold must be greater"
            in str(exc)
        )

    print("[PASS] Test 10 — Invalid configuration rejected.")

    print()
    print("=====================================")
    print("STATISTICAL ANOMALY DETECTOR PASSED")
    print("=====================================")

    return True


if __name__ == "__main__":
    success = run_tests()
    raise SystemExit(0 if success else 1)