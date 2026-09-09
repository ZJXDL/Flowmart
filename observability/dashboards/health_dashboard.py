from __future__ import annotations

import sys
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

ALERTS_ROOT = (
    PROJECT_ROOT
    / "observability"
    / "alerts"
)

for path in (
    METRICS_ROOT,
    ALERTS_ROOT,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from pipeline_metrics import (
    PipelineMetric,
    PipelineMetricsCollector,
)

from observability_alerts import (
    ObservabilityAlert,
    ObservabilityAlertEvaluator,
)


class HealthDashboard:
    """
    Builds a human-readable Flowmart platform health snapshot.

    The dashboard does not own metric collection or alert rules.
    It consumes the existing observability components so that:

        Metrics Collector
              ↓
        Alert Evaluator
              ↓
        Health Dashboard

    remains a clean separation of responsibilities.
    """

    STATUS_SYMBOLS = {
        "HEALTHY": "●",
        "WARNING": "▲",
        "CRITICAL": "■",
        "UNKNOWN": "?",
    }

    def __init__(
        self,
        metrics_collector: PipelineMetricsCollector | None = None,
        alert_evaluator: ObservabilityAlertEvaluator | None = None,
    ):
        self.metrics_collector = (
            metrics_collector
            or PipelineMetricsCollector()
        )

        self.alert_evaluator = (
            alert_evaluator
            or ObservabilityAlertEvaluator()
        )

    # ------------------------------------------------------------------
    # Build dashboard snapshot
    # ------------------------------------------------------------------

    def build_snapshot(
        self,
        metrics: list[PipelineMetric],
    ) -> dict[str, Any]:

        if not isinstance(
            metrics,
            list,
        ):
            raise TypeError(
                "metrics must be a list."
            )

        if not all(
            isinstance(metric, PipelineMetric)
            for metric in metrics
        ):
            raise TypeError(
                "All metrics must be PipelineMetric instances."
            )

        summary = (
            self.metrics_collector.build_summary(
                metrics
            )
        )

        alerts = [
            self.alert_evaluator.evaluate(
                metric
            )
            for metric in metrics
        ]

        return {
            "overall_status": summary[
                "overall_status"
            ],
            "pipeline_count": summary[
                "pipeline_count"
            ],
            "healthy_count": summary[
                "healthy_count"
            ],
            "warning_count": summary[
                "warning_count"
            ],
            "critical_count": summary[
                "critical_count"
            ],
            "unknown_count": summary[
                "unknown_count"
            ],
            "pipelines": [
                metric.to_dict()
                for metric in metrics
            ],
            "alerts": [
                alert.to_dict()
                for alert in alerts
            ],
        }

    # ------------------------------------------------------------------
    # Render dashboard
    # ------------------------------------------------------------------

    def render(
        self,
        snapshot: dict[str, Any],
    ) -> str:

        if not isinstance(
            snapshot,
            dict,
        ):
            raise TypeError(
                "snapshot must be a dictionary."
            )

        overall_status = snapshot.get(
            "overall_status",
            "UNKNOWN",
        )

        pipeline_count = snapshot.get(
            "pipeline_count",
            0,
        )

        healthy_count = snapshot.get(
            "healthy_count",
            0,
        )

        warning_count = snapshot.get(
            "warning_count",
            0,
        )

        critical_count = snapshot.get(
            "critical_count",
            0,
        )

        unknown_count = snapshot.get(
            "unknown_count",
            0,
        )

        pipelines = snapshot.get(
            "pipelines",
            [],
        )

        width = 48

        lines = []

        lines.append(
            "╔" + "═" * width + "╗"
        )

        lines.append(
            "║"
            + "FLOWMART PLATFORM HEALTH".center(width)
            + "║"
        )

        lines.append(
            "╠" + "═" * width + "╣"
        )

        status_symbol = self.STATUS_SYMBOLS.get(
            overall_status,
            "?",
        )

        overall_text = (
            f"{status_symbol} Overall Status: "
            f"{overall_status}"
        )

        lines.append(
            "║ "
            + overall_text.ljust(width - 2)
            + "║"
        )

        lines.append(
            "╠" + "═" * width + "╣"
        )

        if pipelines:

            for pipeline in pipelines:

                name = pipeline.get(
                    "pipeline_name",
                    "unknown",
                )

                status = pipeline.get(
                    "status",
                    "UNKNOWN",
                )

                symbol = self.STATUS_SYMBOLS.get(
                    status,
                    "?",
                )

                display_name = (
                    name[:24].ljust(24)
                )

                status_text = (
                    f"{symbol} {status}"
                )

                content = (
                    f"{display_name} "
                    f"{status_text}"
                )

                lines.append(
                    "║ "
                    + content.ljust(width - 2)
                    + "║"
                )

        else:

            lines.append(
                "║ "
                + "No pipeline metrics available."
                .ljust(width - 2)
                + "║"
            )

        lines.append(
            "╠" + "═" * width + "╣"
        )

        summary_lines = [
            f"Pipelines: {pipeline_count}",
            f"Healthy:   {healthy_count}",
            f"Warnings:  {warning_count}",
            f"Critical:  {critical_count}",
            f"Unknown:   {unknown_count}",
        ]

        for line in summary_lines:

            lines.append(
                "║ "
                + line.ljust(width - 2)
                + "║"
            )

        lines.append(
            "╚" + "═" * width + "╝"
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Render alerts
    # ------------------------------------------------------------------

    def render_alerts(
        self,
        snapshot: dict[str, Any],
    ) -> str:

        alerts = snapshot.get(
            "alerts",
            [],
        )

        if not alerts:
            return (
                "FLOWMART ALERTS\n"
                "===============\n"
                "No alerts."
            )

        lines = [
            "FLOWMART ALERTS",
            "===============",
        ]

        for alert in alerts:

            severity = alert.get(
                "severity",
                "UNKNOWN",
            )

            pipeline_name = alert.get(
                "pipeline_name",
                "unknown",
            )

            alert_type = alert.get(
                "alert_type",
                "UNKNOWN",
            )

            message = alert.get(
                "message",
                "",
            )

            lines.append(
                f"[{severity}] "
                f"{pipeline_name} "
                f"({alert_type})"
            )

            lines.append(
                f"  {message}"
            )

        return "\n".join(lines)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def run_tests() -> bool:

    print(
        "FLOWMART HEALTH DASHBOARD"
    )
    print(
        "========================="
    )

    collector = PipelineMetricsCollector(
        query_tool=None,
    )

    evaluator = ObservabilityAlertEvaluator()

    dashboard = HealthDashboard(
        metrics_collector=collector,
        alert_evaluator=evaluator,
    )

    # --------------------------------------------------------------
    # Test 1 — Healthy snapshot
    # --------------------------------------------------------------

    metrics = [
        PipelineMetric(
            pipeline_name="bronze_orders",
            status="HEALTHY",
            records_processed=5015,
            records_failed=0,
            execution_time_seconds=10,
            last_success_at="2026-09-09T10:00:00+00:00",
            metadata={},
        ),
        PipelineMetric(
            pipeline_name="silver_orders",
            status="HEALTHY",
            records_processed=5015,
            records_failed=0,
            execution_time_seconds=12,
            last_success_at="2026-09-09T10:00:00+00:00",
            metadata={},
        ),
    ]

    snapshot = dashboard.build_snapshot(
        metrics
    )

    assert snapshot[
        "overall_status"
    ] == "HEALTHY"

    assert snapshot[
        "pipeline_count"
    ] == 2

    assert snapshot[
        "healthy_count"
    ] == 2

    print(
        "[PASS] Test 1 — Healthy snapshot."
    )

    # --------------------------------------------------------------
    # Test 2 — Warning snapshot
    # --------------------------------------------------------------

    metrics = [
        PipelineMetric(
            pipeline_name="bronze_orders",
            status="HEALTHY",
            records_processed=5015,
            records_failed=0,
            execution_time_seconds=10,
            last_success_at="2026-09-09T10:00:00+00:00",
            metadata={},
        ),
        PipelineMetric(
            pipeline_name="silver_orders",
            status="WARNING",
            records_processed=5000,
            records_failed=15,
            execution_time_seconds=20,
            last_success_at=None,
            metadata={},
        ),
    ]

    snapshot = dashboard.build_snapshot(
        metrics
    )

    assert snapshot[
        "overall_status"
    ] == "WARNING"

    assert snapshot[
        "warning_count"
    ] == 1

    print(
        "[PASS] Test 2 — Warning snapshot."
    )

    # --------------------------------------------------------------
    # Test 3 — Critical snapshot
    # --------------------------------------------------------------

    metrics = [
        PipelineMetric(
            pipeline_name="bronze_orders",
            status="HEALTHY",
            records_processed=5015,
            records_failed=0,
            execution_time_seconds=10,
            last_success_at="2026-09-09T10:00:00+00:00",
            metadata={},
        ),
        PipelineMetric(
            pipeline_name="flink_orders",
            status="CRITICAL",
            records_processed=0,
            records_failed=5015,
            execution_time_seconds=90,
            last_success_at=None,
            metadata={},
        ),
    ]

    snapshot = dashboard.build_snapshot(
        metrics
    )

    assert snapshot[
        "overall_status"
    ] == "CRITICAL"

    assert snapshot[
        "critical_count"
    ] == 1

    print(
        "[PASS] Test 3 — Critical snapshot."
    )

    # --------------------------------------------------------------
    # Test 4 — Pipeline data preserved
    # --------------------------------------------------------------

    pipeline = snapshot[
        "pipelines"
    ][1]

    assert pipeline[
        "pipeline_name"
    ] == "flink_orders"

    assert pipeline[
        "records_failed"
    ] == 5015

    print(
        "[PASS] Test 4 — Pipeline data preservation."
    )

    # --------------------------------------------------------------
    # Test 5 — Alerts generated
    # --------------------------------------------------------------

    alerts = snapshot[
        "alerts"
    ]

    assert len(alerts) == 2

    assert alerts[0][
        "severity"
    ] == "HEALTHY"

    assert alerts[1][
        "severity"
    ] == "CRITICAL"

    print(
        "[PASS] Test 5 — Alert generation."
    )

    # --------------------------------------------------------------
    # Test 6 — Dashboard rendering
    # --------------------------------------------------------------

    rendered = dashboard.render(
        snapshot
    )

    assert (
        "FLOWMART PLATFORM HEALTH"
        in rendered
    )

    assert (
        "CRITICAL"
        in rendered
    )

    assert (
        "flink_orders"
        in rendered
    )

    assert (
        "Pipelines: 2"
        in rendered
    )

    print(
        "[PASS] Test 6 — Dashboard rendering."
    )

    # --------------------------------------------------------------
    # Test 7 — Alert rendering
    # --------------------------------------------------------------

    rendered_alerts = dashboard.render_alerts(
        snapshot
    )

    assert (
        "FLOWMART ALERTS"
        in rendered_alerts
    )

    assert (
        "flink_orders"
        in rendered_alerts
    )

    assert (
        "PIPELINE_CRITICAL"
        in rendered_alerts
    )

    print(
        "[PASS] Test 7 — Alert rendering."
    )

    # --------------------------------------------------------------
    # Test 8 — Empty snapshot
    # --------------------------------------------------------------

    snapshot = dashboard.build_snapshot(
        []
    )

    assert snapshot[
        "pipeline_count"
    ] == 0

    assert snapshot[
        "overall_status"
    ] == "UNKNOWN"

    rendered = dashboard.render(
        snapshot
    )

    assert (
        "UNKNOWN"
        in rendered
    )

    assert (
        "No pipeline metrics available."
        in rendered
    )

    print(
        "[PASS] Test 8 — Empty snapshot."
    )

    # --------------------------------------------------------------
    # Test 9 — Invalid metrics list
    # --------------------------------------------------------------

    try:

        dashboard.build_snapshot(
            "not-a-list"
        )

        raise AssertionError(
            "Expected TypeError."
        )

    except TypeError as exc:

        assert (
            "metrics must be a list"
            in str(exc)
        )

    print(
        "[PASS] Test 9 — Invalid metrics collection rejected."
    )

    # --------------------------------------------------------------
    # Test 10 — Invalid metric element
    # --------------------------------------------------------------

    try:

        dashboard.build_snapshot(
            ["invalid"]
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
        "[PASS] Test 10 — Invalid metric element rejected."
    )

    # --------------------------------------------------------------
    # Test 11 — Custom alert threshold
    # --------------------------------------------------------------

    custom_evaluator = (
        ObservabilityAlertEvaluator(
            execution_time_warning_seconds=5
        )
    )

    custom_dashboard = HealthDashboard(
        metrics_collector=collector,
        alert_evaluator=custom_evaluator,
    )

    metrics = [
        PipelineMetric(
            pipeline_name="slow_pipeline",
            status="HEALTHY",
            records_processed=100,
            records_failed=0,
            execution_time_seconds=10,
            last_success_at="2026-09-09T10:00:00+00:00",
            metadata={},
        )
    ]

    snapshot = custom_dashboard.build_snapshot(
        metrics
    )

    assert snapshot[
        "overall_status"
    ] == "HEALTHY"

    assert snapshot[
        "alerts"
    ][0][
        "severity"
    ] == "WARNING"

    assert snapshot[
        "alerts"
    ][0][
        "alert_type"
    ] == "SLOW_PIPELINE"

    print(
        "[PASS] Test 11 — Custom alert threshold."
    )

    print()
    print(
        "========================="
    )
    print(
        "HEALTH DASHBOARD PASSED"
    )
    print(
        "========================="
    )

    return True


if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )