from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ----------------------------------------------------------------------
# Flowmart project paths
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AI_ANALYST_SRC = (
    PROJECT_ROOT
    / "apps"
    / "ai-analyst"
    / "src"
)

if str(AI_ANALYST_SRC) not in sys.path:
    sys.path.insert(0, str(AI_ANALYST_SRC))


from tools.trino_tool import TrinoQueryTool


@dataclass
class PipelineMetric:
    """
    Structured operational metric for a Flowmart pipeline.
    """

    pipeline_name: str
    status: str
    records_processed: int
    records_failed: int
    execution_time_seconds: float
    last_success_at: str | None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PipelineMetricsCollector:
    """
    Collects operational metrics for Flowmart pipelines.

    The collector supports:

        - explicit metric recording
        - Trino-backed record counts
        - structured serialization
        - pipeline health summaries

    It deliberately does not depend on a monitoring platform.
    This keeps the observability layer portable and easy to integrate
    with Prometheus, Grafana, Power BI, or another monitoring system later.
    """

    VALID_STATUSES = {
        "HEALTHY",
        "WARNING",
        "CRITICAL",
        "UNKNOWN",
    }

    def __init__(
        self,
        query_tool: TrinoQueryTool | None = None,
    ):
        self.query_tool = (
            query_tool
            or TrinoQueryTool()
        )

    # ------------------------------------------------------------------
    # Record a metric
    # ------------------------------------------------------------------

    def record(
        self,
        pipeline_name: str,
        status: str,
        records_processed: int,
        records_failed: int,
        execution_time_seconds: float,
        last_success_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineMetric:

        if not pipeline_name.strip():
            raise ValueError(
                "pipeline_name must not be empty."
            )

        normalized_status = status.upper()

        if normalized_status not in self.VALID_STATUSES:
            raise ValueError(
                f"Unsupported pipeline status: {status}"
            )

        if records_processed < 0:
            raise ValueError(
                "records_processed must be non-negative."
            )

        if records_failed < 0:
            raise ValueError(
                "records_failed must be non-negative."
            )

        if execution_time_seconds < 0:
            raise ValueError(
                "execution_time_seconds must be non-negative."
            )

        if last_success_at is None:
            if normalized_status == "HEALTHY":
                last_success_at = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

        return PipelineMetric(
            pipeline_name=pipeline_name,
            status=normalized_status,
            records_processed=int(
                records_processed
            ),
            records_failed=int(
                records_failed
            ),
            execution_time_seconds=float(
                execution_time_seconds
            ),
            last_success_at=last_success_at,
            metadata=(
                metadata.copy()
                if metadata
                else {}
            ),
        )

    # ------------------------------------------------------------------
    # Query a table row count
    # ------------------------------------------------------------------

    def get_table_row_count(
        self,
        table_name: str,
    ) -> int:

        if not table_name.strip():
            raise ValueError(
                "table_name must not be empty."
            )

        # Table names cannot safely be parameterized through the
        # Trino client, so only allow simple identifiers.
        if not table_name.replace(
            "_",
            "",
        ).isalnum():
            raise ValueError(
                "table_name contains invalid characters."
            )

        sql = f"""
SELECT COUNT(*) AS row_count
FROM {table_name}
"""

        result = self.query_tool.execute(
            sql
        )

        rows = self._normalize_result(
            result
        )

        if not rows:
            raise ValueError(
                "Trino returned no rows."
            )

        value = rows[0].get(
            "row_count"
        )

        if value is None:
            raise ValueError(
                "Trino result did not contain row_count."
            )

        return int(value)

    # ------------------------------------------------------------------
    # Normalize Trino results
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_result(
        result: Any,
    ) -> list[dict[str, Any]]:

        if isinstance(result, list):

            if not all(
                isinstance(row, dict)
                for row in result
            ):
                raise ValueError(
                    "Query result list must contain dictionaries."
                )

            return result

        if isinstance(result, dict):

            columns = result.get(
                "columns"
            )

            rows = result.get(
                "rows"
            )

            if columns is None or rows is None:
                raise ValueError(
                    "Trino result must contain 'columns' and 'rows'."
                )

            normalized = []

            for row in rows:

                if isinstance(row, dict):
                    normalized.append(row)
                    continue

                if not isinstance(
                    row,
                    (list, tuple),
                ):
                    raise ValueError(
                        "Trino result rows must be dictionaries, "
                        "lists, or tuples."
                    )

                if len(row) != len(columns):
                    raise ValueError(
                        "Trino result row length does not match "
                        "the number of columns."
                    )

                normalized.append(
                    dict(
                        zip(
                            columns,
                            row,
                        )
                    )
                )

            return normalized

        raise ValueError(
            "Unsupported Trino query result format."
        )

    # ------------------------------------------------------------------
    # Build a complete health snapshot
    # ------------------------------------------------------------------

    @staticmethod
    def build_summary(
        metrics: list[PipelineMetric],
    ) -> dict[str, Any]:

        if not isinstance(
            metrics,
            list,
        ):
            raise TypeError(
                "metrics must be a list."
            )

        if not metrics:
            return {
                "pipeline_count": 0,
                "healthy_count": 0,
                "warning_count": 0,
                "critical_count": 0,
                "unknown_count": 0,
                "overall_status": "UNKNOWN",
            }

        healthy_count = sum(
            metric.status == "HEALTHY"
            for metric in metrics
        )

        warning_count = sum(
            metric.status == "WARNING"
            for metric in metrics
        )

        critical_count = sum(
            metric.status == "CRITICAL"
            for metric in metrics
        )

        unknown_count = sum(
            metric.status == "UNKNOWN"
            for metric in metrics
        )

        if critical_count > 0:
            overall_status = "CRITICAL"

        elif warning_count > 0:
            overall_status = "WARNING"

        elif unknown_count > 0:
            overall_status = "UNKNOWN"

        else:
            overall_status = "HEALTHY"

        return {
            "pipeline_count": len(metrics),
            "healthy_count": healthy_count,
            "warning_count": warning_count,
            "critical_count": critical_count,
            "unknown_count": unknown_count,
            "overall_status": overall_status,
        }


# ----------------------------------------------------------------------
# Mock Trino tool
# ----------------------------------------------------------------------


class MockTrinoQueryTool:

    def __init__(
        self,
        result: Any,
    ):
        self.result = result
        self.last_sql = None

    def execute(
        self,
        sql: str,
    ):
        self.last_sql = sql
        return self.result


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def run_tests() -> bool:

    print(
        "FLOWMART PIPELINE METRICS"
    )
    print(
        "========================="
    )

    collector = PipelineMetricsCollector(
        query_tool=MockTrinoQueryTool(
            result=[
                {
                    "row_count": 5015
                }
            ]
        )
    )

    # --------------------------------------------------------------
    # Test 1 — Record healthy pipeline
    # --------------------------------------------------------------

    metric = collector.record(
        pipeline_name="silver_orders",
        status="HEALTHY",
        records_processed=5015,
        records_failed=0,
        execution_time_seconds=12.5,
        last_success_at="2026-09-09T10:00:00+00:00",
    )

    assert metric.pipeline_name == "silver_orders"
    assert metric.status == "HEALTHY"
    assert metric.records_processed == 5015
    assert metric.records_failed == 0
    assert metric.execution_time_seconds == 12.5
    assert (
        metric.last_success_at
        == "2026-09-09T10:00:00+00:00"
    )

    print(
        "[PASS] Test 1 — Healthy pipeline metric."
    )

    # --------------------------------------------------------------
    # Test 2 — Warning pipeline
    # --------------------------------------------------------------

    warning = collector.record(
        pipeline_name="bronze_orders",
        status="warning",
        records_processed=5000,
        records_failed=15,
        execution_time_seconds=25,
        last_success_at=None,
    )

    assert warning.status == "WARNING"
    assert warning.records_failed == 15
    assert warning.last_success_at is None

    print(
        "[PASS] Test 2 — Warning pipeline metric."
    )

    # --------------------------------------------------------------
    # Test 3 — Critical pipeline
    # --------------------------------------------------------------

    critical = collector.record(
        pipeline_name="gold_daily_sales",
        status="CRITICAL",
        records_processed=0,
        records_failed=5000,
        execution_time_seconds=60,
    )

    assert critical.status == "CRITICAL"
    assert critical.records_processed == 0
    assert critical.records_failed == 5000
    assert critical.last_success_at is None

    print(
        "[PASS] Test 3 — Critical pipeline metric."
    )

    # --------------------------------------------------------------
    # Test 4 — Metadata
    # --------------------------------------------------------------

    metric = collector.record(
        pipeline_name="dbt",
        status="HEALTHY",
        records_processed=3,
        records_failed=0,
        execution_time_seconds=4,
        metadata={
            "models": 3,
            "tests_passed": 17,
        },
    )

    assert metric.metadata["models"] == 3
    assert metric.metadata["tests_passed"] == 17

    print(
        "[PASS] Test 4 — Pipeline metadata."
    )

    # --------------------------------------------------------------
    # Test 5 — Dictionary serialization
    # --------------------------------------------------------------

    data = metric.to_dict()

    assert isinstance(
        data,
        dict,
    )

    assert data["pipeline_name"] == "dbt"
    assert data["status"] == "HEALTHY"
    assert data["records_processed"] == 3
    assert data["metadata"]["tests_passed"] == 17

    print(
        "[PASS] Test 5 — Metric serialization."
    )

    # --------------------------------------------------------------
    # Test 6 — Trino row count
    # --------------------------------------------------------------

    count = collector.get_table_row_count(
        "orders"
    )

    assert count == 5015

    assert (
        "SELECT COUNT(*)"
        in collector.query_tool.last_sql
    )

    assert (
        "FROM orders"
        in collector.query_tool.last_sql
    )

    print(
        "[PASS] Test 6 — Trino row count."
    )

    # --------------------------------------------------------------
    # Test 7 — Structured Trino result
    # --------------------------------------------------------------

    structured_collector = PipelineMetricsCollector(
        query_tool=MockTrinoQueryTool(
            result={
                "columns": [
                    "row_count"
                ],
                "rows": [
                    [5015]
                ],
            }
        )
    )

    count = structured_collector.get_table_row_count(
        "orders"
    )

    assert count == 5015

    print(
        "[PASS] Test 7 — Structured Trino result."
    )

    # --------------------------------------------------------------
    # Test 8 — Health summary
    # --------------------------------------------------------------

    metrics = [
        collector.record(
            pipeline_name="bronze",
            status="HEALTHY",
            records_processed=5000,
            records_failed=0,
            execution_time_seconds=5,
        ),
        collector.record(
            pipeline_name="silver",
            status="HEALTHY",
            records_processed=5000,
            records_failed=0,
            execution_time_seconds=6,
        ),
        collector.record(
            pipeline_name="dbt",
            status="WARNING",
            records_processed=3,
            records_failed=1,
            execution_time_seconds=10,
        ),
    ]

    summary = collector.build_summary(
        metrics
    )

    assert summary["pipeline_count"] == 3
    assert summary["healthy_count"] == 2
    assert summary["warning_count"] == 1
    assert summary["critical_count"] == 0
    assert summary["overall_status"] == "WARNING"

    print(
        "[PASS] Test 8 — Health summary."
    )

    # --------------------------------------------------------------
    # Test 9 — Critical dominates overall status
    # --------------------------------------------------------------

    critical_metrics = [
        collector.record(
            pipeline_name="bronze",
            status="HEALTHY",
            records_processed=5000,
            records_failed=0,
            execution_time_seconds=5,
        ),
        collector.record(
            pipeline_name="flink",
            status="WARNING",
            records_processed=4900,
            records_failed=100,
            execution_time_seconds=20,
        ),
        collector.record(
            pipeline_name="gold",
            status="CRITICAL",
            records_processed=0,
            records_failed=5000,
            execution_time_seconds=100,
        ),
    ]

    summary = collector.build_summary(
        critical_metrics
    )

    assert summary["overall_status"] == "CRITICAL"

    print(
        "[PASS] Test 9 — Critical status precedence."
    )

    # --------------------------------------------------------------
    # Test 10 — Empty summary
    # --------------------------------------------------------------

    summary = collector.build_summary(
        []
    )

    assert summary["pipeline_count"] == 0
    assert summary["overall_status"] == "UNKNOWN"

    print(
        "[PASS] Test 10 — Empty summary."
    )

    # --------------------------------------------------------------
    # Test 11 — Invalid pipeline status
    # --------------------------------------------------------------

    try:

        collector.record(
            pipeline_name="test",
            status="BROKEN",
            records_processed=1,
            records_failed=0,
            execution_time_seconds=1,
        )

        raise AssertionError(
            "Expected invalid status error."
        )

    except ValueError as exc:

        assert (
            "Unsupported pipeline status"
            in str(exc)
        )

    print(
        "[PASS] Test 11 — Invalid status rejected."
    )

    # --------------------------------------------------------------
    # Test 12 — Negative records rejected
    # --------------------------------------------------------------

    try:

        collector.record(
            pipeline_name="test",
            status="HEALTHY",
            records_processed=-1,
            records_failed=0,
            execution_time_seconds=1,
        )

        raise AssertionError(
            "Expected negative-record error."
        )

    except ValueError as exc:

        assert (
            "records_processed must be non-negative"
            in str(exc)
        )

    print(
        "[PASS] Test 12 — Negative processed records rejected."
    )

    # --------------------------------------------------------------
    # Test 13 — Invalid table name rejected
    # --------------------------------------------------------------

    try:

        collector.get_table_row_count(
            "orders; DROP TABLE orders"
        )

        raise AssertionError(
            "Expected invalid-table-name error."
        )

    except ValueError as exc:

        assert (
            "invalid characters"
            in str(exc)
        )

    print(
        "[PASS] Test 13 — Invalid table name rejected."
    )

    print()
    print(
        "========================="
    )
    print(
        "PIPELINE METRICS PASSED"
    )
    print(
        "=========================",
    )

    return True


if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )