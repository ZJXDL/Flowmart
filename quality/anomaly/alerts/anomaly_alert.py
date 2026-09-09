from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any

# ----------------------------------------------------------------------
# Flowmart anomaly package path
# ----------------------------------------------------------------------

ANOMALY_ROOT = Path(__file__).resolve().parent.parent

if str(ANOMALY_ROOT) not in sys.path:
    sys.path.insert(0, str(ANOMALY_ROOT))


from detectors.statistical_detector import (
    AnomalyResult,
)


@dataclass
class AnomalyAlert:
    """
    Structured alert generated from an anomaly detection result.
    """

    metric: str
    severity: str
    current_value: float
    baseline_mean: float
    baseline_stddev: float
    z_score: float
    is_anomaly: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "severity": self.severity,
            "current_value": self.current_value,
            "baseline_mean": self.baseline_mean,
            "baseline_stddev": self.baseline_stddev,
            "z_score": self.z_score,
            "is_anomaly": self.is_anomaly,
            "message": self.message,
        }


class AnomalyAlertBuilder:
    """
    Converts statistical anomaly results into structured alerts.

    NORMAL:
        No anomaly was detected.

    WARNING:
        Metric deviates meaningfully from its baseline.

    CRITICAL:
        Metric deviates significantly from its baseline.
    """

    def build(
        self,
        result: AnomalyResult,
    ) -> AnomalyAlert:

        if not isinstance(result, AnomalyResult):
            raise TypeError(
                "result must be an AnomalyResult."
            )

        severity = result.severity.upper()

        if severity == "NORMAL":

            message = (
                f"{result.metric} is within the expected "
                "historical range."
            )

        elif severity == "WARNING":

            direction = (
                "above"
                if result.z_score > 0
                else "below"
            )

            message = (
                f"{result.metric} is {direction} the historical "
                "baseline and should be monitored."
            )

        elif severity == "CRITICAL":

            direction = (
                "above"
                if result.z_score > 0
                else "below"
            )

            message = (
                f"{result.metric} is significantly {direction} "
                "the historical baseline and requires attention."
            )

        else:

            raise ValueError(
                f"Unsupported anomaly severity: {result.severity}"
            )

        return AnomalyAlert(
            metric=result.metric,
            severity=severity,
            current_value=float(
                result.current_value
            ),
            baseline_mean=float(
                result.baseline_mean
            ),
            baseline_stddev=float(
                result.baseline_stddev
            ),
            z_score=float(
                result.z_score
            ),
            is_anomaly=bool(
                result.is_anomaly
            ),
            message=message,
        )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def run_tests() -> bool:

    print(
        "FLOWMART ANOMALY ALERT BUILDER"
    )
    print(
        "=============================="
    )

    builder = AnomalyAlertBuilder()

    # --------------------------------------------------------------
    # Test 1 — NORMAL alert
    # --------------------------------------------------------------

    normal_result = AnomalyResult(
        metric="daily_revenue",
        current_value=1005,
        baseline_mean=1000,
        baseline_stddev=20,
        z_score=0.25,
        is_anomaly=False,
        severity="NORMAL",
    )

    alert = builder.build(
        normal_result
    )

    assert alert.metric == "daily_revenue"
    assert alert.severity == "NORMAL"
    assert alert.current_value == 1005
    assert alert.is_anomaly is False
    assert "within the expected" in alert.message

    print(
        "[PASS] Test 1 — NORMAL alert."
    )

    # --------------------------------------------------------------
    # Test 2 — WARNING above baseline
    # --------------------------------------------------------------

    warning_result = AnomalyResult(
        metric="daily_revenue",
        current_value=1040,
        baseline_mean=1000,
        baseline_stddev=20,
        z_score=2.0,
        is_anomaly=True,
        severity="WARNING",
    )

    alert = builder.build(
        warning_result
    )

    assert alert.severity == "WARNING"
    assert alert.is_anomaly is True
    assert "above" in alert.message
    assert "historical baseline" in alert.message

    print(
        "[PASS] Test 2 — WARNING alert above baseline."
    )

    # --------------------------------------------------------------
    # Test 3 — WARNING below baseline
    # --------------------------------------------------------------

    warning_low_result = AnomalyResult(
        metric="daily_revenue",
        current_value=960,
        baseline_mean=1000,
        baseline_stddev=20,
        z_score=-2.0,
        is_anomaly=True,
        severity="WARNING",
    )

    alert = builder.build(
        warning_low_result
    )

    assert alert.severity == "WARNING"
    assert "below" in alert.message

    print(
        "[PASS] Test 3 — WARNING alert below baseline."
    )

    # --------------------------------------------------------------
    # Test 4 — CRITICAL above baseline
    # --------------------------------------------------------------

    critical_result = AnomalyResult(
        metric="daily_revenue",
        current_value=1100,
        baseline_mean=1000,
        baseline_stddev=25,
        z_score=4.0,
        is_anomaly=True,
        severity="CRITICAL",
    )

    alert = builder.build(
        critical_result
    )

    assert alert.severity == "CRITICAL"
    assert alert.is_anomaly is True
    assert "significantly above" in alert.message
    assert alert.z_score == 4.0

    print(
        "[PASS] Test 4 — CRITICAL alert above baseline."
    )

    # --------------------------------------------------------------
    # Test 5 — CRITICAL below baseline
    # --------------------------------------------------------------

    critical_low_result = AnomalyResult(
        metric="daily_revenue",
        current_value=800,
        baseline_mean=1000,
        baseline_stddev=50,
        z_score=-4.0,
        is_anomaly=True,
        severity="CRITICAL",
    )

    alert = builder.build(
        critical_low_result
    )

    assert alert.severity == "CRITICAL"
    assert "significantly below" in alert.message

    print(
        "[PASS] Test 5 — CRITICAL alert below baseline."
    )

    # --------------------------------------------------------------
    # Test 6 — Dictionary serialization
    # --------------------------------------------------------------

    data = alert.to_dict()

    assert isinstance(
        data,
        dict,
    )

    assert data["metric"] == "daily_revenue"
    assert data["severity"] == "CRITICAL"
    assert data["current_value"] == 800.0
    assert data["baseline_mean"] == 1000.0
    assert data["z_score"] == -4.0
    assert data["is_anomaly"] is True

    print(
        "[PASS] Test 6 — Alert dictionary serialization."
    )

    # --------------------------------------------------------------
    # Test 7 — Invalid result type
    # --------------------------------------------------------------

    try:

        builder.build(
            "not-an-anomaly-result"
        )

        raise AssertionError(
            "Expected TypeError for invalid result."
        )

    except TypeError as exc:

        assert (
            "AnomalyResult"
            in str(exc)
        )

    print(
        "[PASS] Test 7 — Invalid result rejected."
    )

    # --------------------------------------------------------------
    # Test 8 — Unsupported severity
    # --------------------------------------------------------------

    invalid_result = AnomalyResult(
        metric="daily_revenue",
        current_value=1000,
        baseline_mean=1000,
        baseline_stddev=10,
        z_score=0,
        is_anomaly=False,
        severity="UNKNOWN",
    )

    try:

        builder.build(
            invalid_result
        )

        raise AssertionError(
            "Expected ValueError for unsupported severity."
        )

    except ValueError as exc:

        assert (
            "Unsupported anomaly severity"
            in str(exc)
        )

    print(
        "[PASS] Test 8 — Unsupported severity rejected."
    )

    print()
    print(
        "=============================="
    )
    print(
        "ANOMALY ALERT BUILDER PASSED"
    )
    print(
        "=============================="
    )

    return True


if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )