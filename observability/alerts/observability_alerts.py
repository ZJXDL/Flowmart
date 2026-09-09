from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------
# Flowmart project paths
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

METRICS_ROOT = (
    PROJECT_ROOT
    / "observability"
    / "metrics"
)

if str(METRICS_ROOT) not in sys.path:
    sys.path.insert(0, str(METRICS_ROOT))


from pipeline_metrics import PipelineMetric


@dataclass
class ObservabilityAlert:
    """
    Structured operational alert produced from a PipelineMetric.
    """

    pipeline_name: str
    severity: str
    alert_type: str
    message: str
    records_processed: int
    records_failed: int
    execution_time_seconds: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ObservabilityAlertEvaluator:
    """
    Evaluates pipeline metrics and produces operational alerts.

    Rules:

        CRITICAL
        --------
        - Pipeline status is CRITICAL.
        - Records processed == 0 while failures > 0.

        WARNING
        -------
        - Pipeline status is WARNING.
        - Failed records > 0.
        - Execution time exceeds the configured threshold.

        HEALTHY
        -------
        - No operational problems detected.
    """

    def __init__(
        self,
        execution_time_warning_seconds: float = 60.0,
    ):
        if execution_time_warning_seconds <= 0:
            raise ValueError(
                "execution_time_warning_seconds must be greater than 0."
            )

        self.execution_time_warning_seconds = float(
            execution_time_warning_seconds
        )

    # ------------------------------------------------------------------
    # Evaluate a metric
    # ------------------------------------------------------------------

    def evaluate(
        self,
        metric: PipelineMetric,
    ) -> ObservabilityAlert:

        if not isinstance(
            metric,
            PipelineMetric,
        ):
            raise TypeError(
                "metric must be a PipelineMetric."
            )

        # --------------------------------------------------------------
        # CRITICAL — explicit pipeline failure
        # --------------------------------------------------------------

        if metric.status == "CRITICAL":

            return self._build_alert(
                metric=metric,
                severity="CRITICAL",
                alert_type="PIPELINE_CRITICAL",
                message=(
                    f"Pipeline '{metric.pipeline_name}' "
                    "is in a critical state."
                ),
            )

        # --------------------------------------------------------------
        # CRITICAL — failed completely
        # --------------------------------------------------------------

        if (
            metric.records_processed == 0
            and metric.records_failed > 0
        ):

            return self._build_alert(
                metric=metric,
                severity="CRITICAL",
                alert_type="PIPELINE_NO_OUTPUT",
                message=(
                    f"Pipeline '{metric.pipeline_name}' "
                    "processed zero records and reported "
                    f"{metric.records_failed} failures."
                ),
            )

        # --------------------------------------------------------------
        # WARNING — explicit warning state
        # --------------------------------------------------------------

        if metric.status == "WARNING":

            return self._build_alert(
                metric=metric,
                severity="WARNING",
                alert_type="PIPELINE_WARNING",
                message=(
                    f"Pipeline '{metric.pipeline_name}' "
                    "reported a warning state."
                ),
            )

        # --------------------------------------------------------------
        # WARNING — failed records
        # --------------------------------------------------------------

        if metric.records_failed > 0:

            return self._build_alert(
                metric=metric,
                severity="WARNING",
                alert_type="RECORD_FAILURES",
                message=(
                    f"Pipeline '{metric.pipeline_name}' "
                    f"reported {metric.records_failed} "
                    "failed records."
                ),
            )

        # --------------------------------------------------------------
        # WARNING — execution time
        # --------------------------------------------------------------

        if (
            metric.execution_time_seconds
            > self.execution_time_warning_seconds
        ):

            return self._build_alert(
                metric=metric,
                severity="WARNING",
                alert_type="SLOW_PIPELINE",
                message=(
                    f"Pipeline '{metric.pipeline_name}' "
                    f"took {metric.execution_time_seconds:.2f} "
                    "seconds, exceeding the configured "
                    f"threshold of "
                    f"{self.execution_time_warning_seconds:.2f} seconds."
                ),
            )

        # --------------------------------------------------------------
        # HEALTHY
        # --------------------------------------------------------------

        return self._build_alert(
            metric=metric,
            severity="HEALTHY",
            alert_type="NONE",
            message=(
                f"Pipeline '{metric.pipeline_name}' "
                "is operating normally."
            ),
        )

    # ------------------------------------------------------------------
    # Build alert
    # ------------------------------------------------------------------

    @staticmethod
    def _build_alert(
        metric: PipelineMetric,
        severity: str,
        alert_type: str,
        message: str,
    ) -> ObservabilityAlert:

        return ObservabilityAlert(
            pipeline_name=metric.pipeline_name,
            severity=severity,
            alert_type=alert_type,
            message=message,
            records_processed=metric.records_processed,
            records_failed=metric.records_failed,
            execution_time_seconds=metric.execution_time_seconds,
            metadata=metric.metadata.copy(),
        )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def run_tests() -> bool:

    print(
        "FLOWMART OBSERVABILITY ALERTS"
    )
    print(
        "============================"
    )

    evaluator = ObservabilityAlertEvaluator()

    # --------------------------------------------------------------
    # Test 1 — Healthy pipeline
    # --------------------------------------------------------------

    healthy_metric = PipelineMetric(
        pipeline_name="bronze_orders",
        status="HEALTHY",
        records_processed=5015,
        records_failed=0,
        execution_time_seconds=10,
        last_success_at="2026-09-09T10:00:00+00:00",
        metadata={},
    )

    alert = evaluator.evaluate(
        healthy_metric
    )

    assert alert.severity == "HEALTHY"
    assert alert.alert_type == "NONE"
    assert alert.records_failed == 0
    assert "operating normally" in alert.message

    print(
        "[PASS] Test 1 — Healthy pipeline."
    )

    # --------------------------------------------------------------
    # Test 2 — Explicit warning
    # --------------------------------------------------------------

    warning_metric = PipelineMetric(
        pipeline_name="silver_orders",
        status="WARNING",
        records_processed=5000,
        records_failed=15,
        execution_time_seconds=20,
        last_success_at=None,
        metadata={},
    )

    alert = evaluator.evaluate(
        warning_metric
    )

    assert alert.severity == "WARNING"
    assert alert.alert_type == "PIPELINE_WARNING"

    print(
        "[PASS] Test 2 — Explicit warning."
    )

    # --------------------------------------------------------------
    # Test 3 — Record failures
    # --------------------------------------------------------------

    failure_metric = PipelineMetric(
        pipeline_name="bronze_orders",
        status="HEALTHY",
        records_processed=5000,
        records_failed=10,
        execution_time_seconds=20,
        last_success_at="2026-09-09T10:00:00+00:00",
        metadata={},
    )

    alert = evaluator.evaluate(
        failure_metric
    )

    assert alert.severity == "WARNING"
    assert alert.alert_type == "RECORD_FAILURES"
    assert alert.records_failed == 10

    print(
        "[PASS] Test 3 — Record failure alert."
    )

    # --------------------------------------------------------------
    # Test 4 — Slow pipeline
    # --------------------------------------------------------------

    slow_metric = PipelineMetric(
        pipeline_name="gold_daily_sales",
        status="HEALTHY",
        records_processed=5015,
        records_failed=0,
        execution_time_seconds=75,
        last_success_at="2026-09-09T10:00:00+00:00",
        metadata={},
    )

    alert = evaluator.evaluate(
        slow_metric
    )

    assert alert.severity == "WARNING"
    assert alert.alert_type == "SLOW_PIPELINE"
    assert "75.00" in alert.message

    print(
        "[PASS] Test 4 — Slow pipeline alert."
    )

    # --------------------------------------------------------------
    # Test 5 — Explicit critical status
    # --------------------------------------------------------------

    critical_metric = PipelineMetric(
        pipeline_name="flink_orders",
        status="CRITICAL",
        records_processed=0,
        records_failed=5015,
        execution_time_seconds=90,
        last_success_at=None,
        metadata={},
    )

    alert = evaluator.evaluate(
        critical_metric
    )

    assert alert.severity == "CRITICAL"
    assert alert.alert_type == "PIPELINE_CRITICAL"

    print(
        "[PASS] Test 5 — Critical pipeline alert."
    )

    # --------------------------------------------------------------
    # Test 6 — Zero output with failures
    # --------------------------------------------------------------

    zero_output_metric = PipelineMetric(
        pipeline_name="dbt",
        status="HEALTHY",
        records_processed=0,
        records_failed=3,
        execution_time_seconds=5,
        last_success_at=None,
        metadata={},
    )

    alert = evaluator.evaluate(
        zero_output_metric
    )

    assert alert.severity == "CRITICAL"
    assert alert.alert_type == "PIPELINE_NO_OUTPUT"
    assert "zero records" in alert.message

    print(
        "[PASS] Test 6 — Zero-output pipeline."
    )

    # --------------------------------------------------------------
    # Test 7 — Metadata preserved
    # --------------------------------------------------------------

    metadata_metric = PipelineMetric(
        pipeline_name="dbt",
        status="WARNING",
        records_processed=3,
        records_failed=1,
        execution_time_seconds=20,
        last_success_at=None,
        metadata={
            "models": 3,
            "tests_passed": 17,
        },
    )

    alert = evaluator.evaluate(
        metadata_metric
    )

    assert alert.metadata["models"] == 3
    assert alert.metadata["tests_passed"] == 17

    print(
        "[PASS] Test 7 — Metadata preservation."
    )

    # --------------------------------------------------------------
    # Test 8 — Serialization
    # --------------------------------------------------------------

    data = alert.to_dict()

    assert isinstance(
        data,
        dict,
    )

    assert data["pipeline_name"] == "dbt"
    assert data["severity"] == "WARNING"
    assert data["alert_type"] == "PIPELINE_WARNING"
    assert data["records_processed"] == 3

    print(
        "[PASS] Test 8 — Alert serialization."
    )

    # --------------------------------------------------------------
    # Test 9 — Custom execution threshold
    # --------------------------------------------------------------

    custom_evaluator = ObservabilityAlertEvaluator(
        execution_time_warning_seconds=10
    )

    metric = PipelineMetric(
        pipeline_name="test_pipeline",
        status="HEALTHY",
        records_processed=100,
        records_failed=0,
        execution_time_seconds=11,
        last_success_at="2026-09-09T10:00:00+00:00",
        metadata={},
    )

    alert = custom_evaluator.evaluate(
        metric
    )

    assert alert.severity == "WARNING"
    assert alert.alert_type == "SLOW_PIPELINE"

    print(
        "[PASS] Test 9 — Custom execution threshold."
    )

    # --------------------------------------------------------------
    # Test 10 — Invalid metric type
    # --------------------------------------------------------------

    try:

        evaluator.evaluate(
            "not-a-pipeline-metric"
        )

        raise AssertionError(
            "Expected TypeError."
        )

    except TypeError as exc:

        assert (
            "PipelineMetric"
            in str(exc)
        )

    print(
        "[PASS] Test 10 — Invalid metric rejected."
    )

    # --------------------------------------------------------------
    # Test 11 — Invalid threshold
    # --------------------------------------------------------------

    try:

        ObservabilityAlertEvaluator(
            execution_time_warning_seconds=0
        )

        raise AssertionError(
            "Expected invalid-threshold error."
        )

    except ValueError as exc:

        assert (
            "greater than 0"
            in str(exc)
        )

    print(
        "[PASS] Test 11 — Invalid threshold rejected."
    )

    print()
    print(
        "============================"
    )
    print(
        "OBSERVABILITY ALERTS PASSED"
    )
    print(
        "============================"
    )

    return True


if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )