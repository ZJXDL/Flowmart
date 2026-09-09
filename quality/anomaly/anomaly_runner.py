from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------
# Flowmart project paths
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

AI_ANALYST_SRC = (
    PROJECT_ROOT
    / "apps"
    / "ai-analyst"
    / "src"
)

ANOMALY_ROOT = (
    PROJECT_ROOT
    / "quality"
    / "anomaly"
)

if str(AI_ANALYST_SRC) not in sys.path:
    sys.path.insert(0, str(AI_ANALYST_SRC))

if str(ANOMALY_ROOT) not in sys.path:
    sys.path.insert(0, str(ANOMALY_ROOT))


from anomaly_service import (
    AnomalyDetectionService,
)

from alerts.anomaly_alert import (
    AnomalyAlert,
    AnomalyAlertBuilder,
)


class AnomalyRunner:
    """
    Flowmart anomaly detection orchestrator.

    Pipeline:

        Analytical Data
              ↓
        Detection Service
              ↓
        Statistical Detector
              ↓
          AnomalyResult
              ↓
          Alert Builder
              ↓
          AnomalyAlert
    """

    def __init__(
        self,
        detection_service: AnomalyDetectionService | None = None,
        alert_builder: AnomalyAlertBuilder | None = None,
    ):
        self.detection_service = (
            detection_service
            or AnomalyDetectionService()
        )

        self.alert_builder = (
            alert_builder
            or AnomalyAlertBuilder()
        )

    # ------------------------------------------------------------------
    # Generic detection
    # ------------------------------------------------------------------

    def run(
        self,
        metric: str,
        history_rows: list[dict[str, Any]],
        value_column: str,
    ) -> AnomalyAlert:
        """
        Run anomaly detection on supplied historical data.

        history_rows must be ordered:

            newest → oldest
        """

        if not metric.strip():
            raise ValueError(
                "metric must not be empty."
            )

        if not value_column.strip():
            raise ValueError(
                "value_column must not be empty."
            )

        result = self.detection_service.detect_from_history(
            metric=metric,
            history_rows=history_rows,
            value_column=value_column,
        )

        return self.alert_builder.build(
            result
        )

    # ------------------------------------------------------------------
    # Daily revenue detection
    # ------------------------------------------------------------------

    def run_daily_revenue(
        self,
        days: int = 30,
    ) -> AnomalyAlert:
        """
        Run the complete daily revenue anomaly pipeline
        against Flowmart's analytical orders model.
        """

        result = (
            self.detection_service
            .detect_daily_revenue(
                days=days
            )
        )

        return self.alert_builder.build(
            result
        )


# ----------------------------------------------------------------------
# Mock detection service used by tests
# ----------------------------------------------------------------------


class MockDetectionService:
    """
    Deterministic detection service used for runner tests.
    """

    def __init__(
        self,
        result,
    ):
        self.result = result
        self.calls = []

    def detect_from_history(
        self,
        metric,
        history_rows,
        value_column,
    ):
        self.calls.append(
            {
                "metric": metric,
                "history_rows": history_rows,
                "value_column": value_column,
            }
        )

        return self.result

    def detect_daily_revenue(
        self,
        days=30,
    ):
        self.calls.append(
            {
                "metric": "daily_revenue",
                "days": days,
            }
        )

        return self.result


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def run_tests() -> bool:

    print(
        "FLOWMART ANOMALY RUNNER"
    )
    print(
        "======================"
    )

    # --------------------------------------------------------------
    # Shared test result
    # --------------------------------------------------------------

    from detectors.statistical_detector import (
        AnomalyResult,
    )

    warning_result = AnomalyResult(
        metric="daily_revenue",
        current_value=1040,
        baseline_mean=1000,
        baseline_stddev=20,
        z_score=2.0,
        is_anomaly=True,
        severity="WARNING",
    )

    mock_service = MockDetectionService(
        result=warning_result
    )

    runner = AnomalyRunner(
        detection_service=mock_service
    )

    # --------------------------------------------------------------
    # Test 1 — Generic pipeline
    # --------------------------------------------------------------

    history = [
        {
            "metric_date": "2026-09-09",
            "daily_revenue": 1040,
        },
        {
            "metric_date": "2026-09-08",
            "daily_revenue": 1000,
        },
        {
            "metric_date": "2026-09-07",
            "daily_revenue": 990,
        },
        {
            "metric_date": "2026-09-06",
            "daily_revenue": 1010,
        },
    ]

    alert = runner.run(
        metric="daily_revenue",
        history_rows=history,
        value_column="daily_revenue",
    )

    assert isinstance(
        alert,
        AnomalyAlert,
    )

    assert alert.metric == "daily_revenue"
    assert alert.severity == "WARNING"
    assert alert.is_anomaly is True
    assert alert.z_score == 2.0

    print(
        "[PASS] Test 1 — Generic anomaly pipeline."
    )

    # --------------------------------------------------------------
    # Test 2 — Service received correct parameters
    # --------------------------------------------------------------

    assert len(
        mock_service.calls
    ) == 1

    call = mock_service.calls[0]

    assert call["metric"] == "daily_revenue"
    assert call["value_column"] == "daily_revenue"
    assert call["history_rows"] == history

    print(
        "[PASS] Test 2 — Detection service parameters."
    )

    # --------------------------------------------------------------
    # Test 3 — Daily revenue convenience pipeline
    # --------------------------------------------------------------

    daily_runner = AnomalyRunner(
        detection_service=mock_service
    )

    alert = daily_runner.run_daily_revenue(
        days=30
    )

    assert isinstance(
        alert,
        AnomalyAlert,
    )

    assert alert.metric == "daily_revenue"
    assert alert.severity == "WARNING"

    assert (
        mock_service.calls[-1]["metric"]
        == "daily_revenue"
    )

    assert (
        mock_service.calls[-1]["days"]
        == 30
    )

    print(
        "[PASS] Test 3 — Daily revenue pipeline."
    )

    # --------------------------------------------------------------
    # Test 4 — Critical anomaly propagation
    # --------------------------------------------------------------

    critical_result = AnomalyResult(
        metric="daily_revenue",
        current_value=1200,
        baseline_mean=1000,
        baseline_stddev=50,
        z_score=4.0,
        is_anomaly=True,
        severity="CRITICAL",
    )

    critical_service = MockDetectionService(
        result=critical_result
    )

    critical_runner = AnomalyRunner(
        detection_service=critical_service
    )

    alert = critical_runner.run(
        metric="daily_revenue",
        history_rows=history,
        value_column="daily_revenue",
    )

    assert alert.severity == "CRITICAL"
    assert alert.is_anomaly is True
    assert alert.z_score == 4.0
    assert "significantly above" in alert.message

    print(
        "[PASS] Test 4 — CRITICAL anomaly propagation."
    )

    # --------------------------------------------------------------
    # Test 5 — Normal result propagation
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

    normal_service = MockDetectionService(
        result=normal_result
    )

    normal_runner = AnomalyRunner(
        detection_service=normal_service
    )

    alert = normal_runner.run(
        metric="daily_revenue",
        history_rows=history,
        value_column="daily_revenue",
    )

    assert alert.severity == "NORMAL"
    assert alert.is_anomaly is False
    assert "within the expected" in alert.message

    print(
        "[PASS] Test 5 — NORMAL result propagation."
    )

    # --------------------------------------------------------------
    # Test 6 — Empty metric rejected
    # --------------------------------------------------------------

    try:

        runner.run(
            metric="",
            history_rows=history,
            value_column="daily_revenue",
        )

        raise AssertionError(
            "Expected empty metric error."
        )

    except ValueError as exc:

        assert (
            "metric must not be empty"
            in str(exc)
        )

    print(
        "[PASS] Test 6 — Empty metric rejected."
    )

    # --------------------------------------------------------------
    # Test 7 — Empty value column rejected
    # --------------------------------------------------------------

    try:

        runner.run(
            metric="daily_revenue",
            history_rows=history,
            value_column="",
        )

        raise AssertionError(
            "Expected empty value column error."
        )

    except ValueError as exc:

        assert (
            "value_column must not be empty"
            in str(exc)
        )

    print(
        "[PASS] Test 7 — Empty value column rejected."
    )

    # --------------------------------------------------------------
    # Test 8 — Alert serialization
    # --------------------------------------------------------------

    serialized = alert.to_dict()

    assert isinstance(
        serialized,
        dict,
    )

    assert serialized["metric"] == "daily_revenue"
    assert serialized["severity"] == "NORMAL"
    assert serialized["is_anomaly"] is False

    print(
        "[PASS] Test 8 — Alert serialization."
    )

    print()
    print(
        "======================"
    )
    print(
        "ANOMALY RUNNER PASSED"
    )
    print(
        "======================"
    )

    return True


if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )