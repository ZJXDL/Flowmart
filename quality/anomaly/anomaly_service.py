from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# Flowmart project paths
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AI_ANALYST_SRC = (
    PROJECT_ROOT
    / "apps"
    / "ai-analyst"
    / "src"
)

ANOMALY_ROOT = Path(__file__).resolve().parent

if str(AI_ANALYST_SRC) not in sys.path:
    sys.path.insert(0, str(AI_ANALYST_SRC))

if str(ANOMALY_ROOT) not in sys.path:
    sys.path.insert(0, str(ANOMALY_ROOT))


from tools.trino_tool import TrinoQueryTool

from detectors.statistical_detector import (
    AnomalyResult,
    StatisticalAnomalyDetector,
)


class AnomalyDetectionService:
    """
    Flowmart autonomous anomaly detection service.

    Responsibilities:

        1. Query analytical data through Trino.
        2. Normalize Trino results into rows.
        3. Build a historical baseline.
        4. Compare the latest observation against that baseline.
        5. Produce a structured AnomalyResult.

    Architecture:

        dbt / Iceberg
              ↓
            Trino
              ↓
        Anomaly Service
              ↓
       Statistical Detector
              ↓
        AnomalyResult
    """

    def __init__(
        self,
        query_tool: TrinoQueryTool | None = None,
        detector: StatisticalAnomalyDetector | None = None,
    ):
        self.query_tool = (
            query_tool
            or TrinoQueryTool()
        )

        self.detector = (
            detector
            or StatisticalAnomalyDetector()
        )

    # ------------------------------------------------------------------
    # Normalize Trino results
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_query_result(
        result: Any,
    ) -> list[dict[str, Any]]:
        """
        Convert the result returned by TrinoQueryTool into:

            list[dict[str, Any]]

        Supported inputs:

            1. list of dictionaries
            2. dictionary containing:
                   {
                       "columns": [...],
                       "rows": [...]
                   }

        This keeps the anomaly service independent from the exact
        presentation format used by the query tool.
        """

        # --------------------------------------------------------------
        # Case 1 — already a list of dictionaries.
        # --------------------------------------------------------------

        if isinstance(result, list):
            if not all(
                isinstance(row, dict)
                for row in result
            ):
                raise ValueError(
                    "Query result list must contain dictionaries."
                )

            return result

        # --------------------------------------------------------------
        # Case 2 — structured Trino result.
        # --------------------------------------------------------------

        if isinstance(result, dict):
            columns = result.get("columns")
            rows = result.get("rows")

            if columns is None or rows is None:
                raise ValueError(
                    "Trino result must contain 'columns' and 'rows'."
                )

            if not isinstance(columns, list):
                raise ValueError(
                    "Trino result 'columns' must be a list."
                )

            if not isinstance(rows, list):
                raise ValueError(
                    "Trino result 'rows' must be a list."
                )

            normalized_rows = []

            for row in rows:
                if isinstance(row, dict):
                    normalized_rows.append(row)
                    continue

                if not isinstance(row, (list, tuple)):
                    raise ValueError(
                        "Trino result rows must be dictionaries, "
                        "lists, or tuples."
                    )

                if len(row) != len(columns):
                    raise ValueError(
                        "Trino result row length does not match "
                        "the number of columns."
                    )

                normalized_rows.append(
                    dict(zip(columns, row))
                )

            return normalized_rows

        raise ValueError(
            "Unsupported Trino query result format."
        )

    # ------------------------------------------------------------------
    # Query analytical metric history
    # ------------------------------------------------------------------

    def get_daily_metric_history(
        self,
        metric_expression: str,
        metric_alias: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Retrieve daily historical values from Flowmart's trusted
        analytical orders model.
        """

        if not metric_expression.strip():
            raise ValueError(
                "metric_expression must not be empty."
            )

        if not metric_alias.strip():
            raise ValueError(
                "metric_alias must not be empty."
            )

        if days < 2:
            raise ValueError(
                "days must be at least 2."
            )

        sql = f"""
SELECT
    CAST(created_at AS DATE) AS metric_date,
    {metric_expression} AS {metric_alias}
FROM orders
WHERE created_at IS NOT NULL
GROUP BY CAST(created_at AS DATE)
ORDER BY metric_date DESC
LIMIT {int(days)}
"""

        result = self.query_tool.execute(sql)

        return self._normalize_query_result(
            result
        )

    # ------------------------------------------------------------------
    # Detect anomaly from historical rows
    # ------------------------------------------------------------------

    def detect_from_history(
        self,
        metric: str,
        history_rows: list[dict[str, Any]],
        value_column: str,
    ) -> AnomalyResult:
        """
        Detect whether the latest value is anomalous.

        Rows must be ordered newest → oldest.
        """

        if not history_rows:
            raise ValueError(
                "history_rows must not be empty."
            )

        if not value_column.strip():
            raise ValueError(
                "value_column must not be empty."
            )

        if len(history_rows) < self.detector.min_history + 1:
            raise ValueError(
                "At least "
                f"{self.detector.min_history + 1} rows are required "
                "so the latest observation can be compared against "
                "historical observations."
            )

        current_row = history_rows[0]

        if value_column not in current_row:
            raise ValueError(
                f"Column '{value_column}' was not found "
                "in the latest row."
            )

        current_value = current_row[value_column]

        historical_values = []

        for row in history_rows[1:]:
            if value_column not in row:
                raise ValueError(
                    f"Column '{value_column}' was not found "
                    "in a historical row."
                )

            historical_values.append(
                row[value_column]
            )

        return self.detector.detect(
            metric=metric,
            current_value=current_value,
            historical_values=historical_values,
        )

    # ------------------------------------------------------------------
    # Daily revenue convenience method
    # ------------------------------------------------------------------

    def detect_daily_revenue(
        self,
        days: int = 30,
    ) -> AnomalyResult:
        """
        Detect an anomaly in daily revenue.
        """

        rows = self.get_daily_metric_history(
            metric_expression="SUM(total_amount)",
            metric_alias="daily_revenue",
            days=days,
        )

        return self.detect_from_history(
            metric="daily_revenue",
            history_rows=rows,
            value_column="daily_revenue",
        )


# ----------------------------------------------------------------------
# Mock Trino query tool used by tests.
# ----------------------------------------------------------------------


class MockTrinoQueryTool:
    """
    Deterministic Trino replacement used for local unit tests.
    """

    def __init__(
        self,
        result: Any,
    ):
        self.result = result
        self.last_sql = None

    def execute(self, sql: str):
        self.last_sql = sql
        return self.result


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def run_tests() -> bool:
    print("FLOWMART ANOMALY DETECTION SERVICE")
    print("=================================")

    mock_rows = [
        {
            "metric_date": "2026-09-09",
            "daily_revenue": 1018,
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
        {
            "metric_date": "2026-09-05",
            "daily_revenue": 1005,
        },
        {
            "metric_date": "2026-09-04",
            "daily_revenue": 995,
        },
    ]

    mock_tool = MockTrinoQueryTool(
        result=mock_rows
    )

    service = AnomalyDetectionService(
        query_tool=mock_tool
    )

    # --------------------------------------------------------------
    # Test 1 — List result normalization
    # --------------------------------------------------------------

    rows = service.get_daily_metric_history(
        metric_expression="SUM(total_amount)",
        metric_alias="daily_revenue",
        days=30,
    )

    assert len(rows) == 6
    assert rows[0]["daily_revenue"] == 1018
    assert "FROM orders" in mock_tool.last_sql
    assert "SUM(total_amount)" in mock_tool.last_sql
    assert "GROUP BY CAST(created_at AS DATE)" in mock_tool.last_sql

    print(
        "[PASS] Test 1 — List result normalization."
    )

    # --------------------------------------------------------------
    # Test 2 — Warning anomaly
    # --------------------------------------------------------------

    result = service.detect_from_history(
        metric="daily_revenue",
        history_rows=mock_rows,
        value_column="daily_revenue",
    )

    assert result.is_anomaly is True
    assert result.severity == "WARNING"

    print(
        "[PASS] Test 2 — Warning anomaly detection."
    )

    # --------------------------------------------------------------
    # Test 3 — Normal metric
    # --------------------------------------------------------------

    normal_rows = [
        {
            "metric_date": "2026-09-09",
            "daily_revenue": 1010,
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
            "daily_revenue": 1015,
        },
        {
            "metric_date": "2026-09-05",
            "daily_revenue": 1005,
        },
        {
            "metric_date": "2026-09-04",
            "daily_revenue": 995,
        },
    ]

    result = service.detect_from_history(
        metric="daily_revenue",
        history_rows=normal_rows,
        value_column="daily_revenue",
    )

    assert result.is_anomaly is False
    assert result.severity == "NORMAL"

    print(
        "[PASS] Test 3 — Normal metric detection."
    )

    # --------------------------------------------------------------
    # Test 4 — Critical anomaly
    # --------------------------------------------------------------

    critical_rows = [
        {
            "metric_date": "2026-09-09",
            "daily_revenue": 1100,
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
        {
            "metric_date": "2026-09-05",
            "daily_revenue": 1005,
        },
        {
            "metric_date": "2026-09-04",
            "daily_revenue": 995,
        },
    ]

    result = service.detect_from_history(
        metric="daily_revenue",
        history_rows=critical_rows,
        value_column="daily_revenue",
    )

    assert result.is_anomaly is True
    assert result.severity == "CRITICAL"

    print(
        "[PASS] Test 4 — Critical anomaly detection."
    )

    # --------------------------------------------------------------
    # Test 5 — Insufficient history
    # --------------------------------------------------------------

    try:
        service.detect_from_history(
            metric="daily_revenue",
            history_rows=[
                {
                    "metric_date": "2026-09-09",
                    "daily_revenue": 1000,
                },
                {
                    "metric_date": "2026-09-08",
                    "daily_revenue": 990,
                },
                {
                    "metric_date": "2026-09-07",
                    "daily_revenue": 1010,
                },
            ],
            value_column="daily_revenue",
        )

        raise AssertionError(
            "Expected insufficient-history error."
        )

    except ValueError as exc:
        assert "rows are required" in str(exc)

    print(
        "[PASS] Test 5 — Insufficient history rejected."
    )

    # --------------------------------------------------------------
    # Test 6 — Missing metric column
    # --------------------------------------------------------------

    try:
        service.detect_from_history(
            metric="daily_revenue",
            history_rows=[
                {
                    "metric_date": "2026-09-09",
                    "revenue": 1000,
                },
                {
                    "metric_date": "2026-09-08",
                    "revenue": 990,
                },
                {
                    "metric_date": "2026-09-07",
                    "revenue": 1010,
                },
                {
                    "metric_date": "2026-09-06",
                    "revenue": 1005,
                },
            ],
            value_column="daily_revenue",
        )

        raise AssertionError(
            "Expected missing-column error."
        )

    except ValueError as exc:
        assert (
            "Column 'daily_revenue' was not found"
            in str(exc)
        )

    print(
        "[PASS] Test 6 — Missing metric column rejected."
    )

    # --------------------------------------------------------------
    # Test 7 — Invalid days
    # --------------------------------------------------------------

    try:
        service.get_daily_metric_history(
            metric_expression="SUM(total_amount)",
            metric_alias="daily_revenue",
            days=1,
        )

        raise AssertionError(
            "Expected invalid-days error."
        )

    except ValueError as exc:
        assert (
            "days must be at least 2"
            in str(exc)
        )

    print(
        "[PASS] Test 7 — Invalid days rejected."
    )

    # --------------------------------------------------------------
    # Test 8 — Empty metric expression
    # --------------------------------------------------------------

    try:
        service.get_daily_metric_history(
            metric_expression="",
            metric_alias="daily_revenue",
            days=30,
        )

        raise AssertionError(
            "Expected empty-expression error."
        )

    except ValueError as exc:
        assert (
            "metric_expression must not be empty"
            in str(exc)
        )

    print(
        "[PASS] Test 8 — Empty metric expression rejected."
    )

    # --------------------------------------------------------------
    # Test 9 — Custom detector injection
    # --------------------------------------------------------------

    custom_detector = StatisticalAnomalyDetector(
        warning_threshold=1.5,
        critical_threshold=2.5,
    )

    custom_service = AnomalyDetectionService(
        query_tool=mock_tool,
        detector=custom_detector,
    )

    assert (
        custom_service.detector.warning_threshold
        == 1.5
    )

    assert (
        custom_service.detector.critical_threshold
        == 2.5
    )

    print(
        "[PASS] Test 9 — Custom detector injection."
    )

    # --------------------------------------------------------------
    # Test 10 — Daily revenue convenience method
    # --------------------------------------------------------------

    result = service.detect_daily_revenue(
        days=30
    )

    assert result.metric == "daily_revenue"
    assert result.severity == "WARNING"

    print(
        "[PASS] Test 10 — Daily revenue detection."
    )

    # --------------------------------------------------------------
    # Test 11 — Structured Trino result
    # --------------------------------------------------------------

    structured_result = {
        "columns": [
            "metric_date",
            "daily_revenue",
        ],
        "rows": [
            [
                "2026-09-09",
                1018,
            ],
            [
                "2026-09-08",
                1000,
            ],
            [
                "2026-09-07",
                990,
            ],
            [
                "2026-09-06",
                1010,
            ],
            [
                "2026-09-05",
                1005,
            ],
            [
                "2026-09-04",
                995,
            ],
        ],
    }

    structured_tool = MockTrinoQueryTool(
        result=structured_result
    )

    structured_service = AnomalyDetectionService(
        query_tool=structured_tool
    )

    rows = structured_service.get_daily_metric_history(
        metric_expression="SUM(total_amount)",
        metric_alias="daily_revenue",
        days=30,
    )

    assert len(rows) == 6
    assert rows[0]["metric_date"] == "2026-09-09"
    assert rows[0]["daily_revenue"] == 1018

    result = structured_service.detect_daily_revenue(
        days=30
    )

    assert result.metric == "daily_revenue"
    assert result.severity == "WARNING"

    print(
        "[PASS] Test 11 — Structured Trino result normalization."
    )

    print()
    print("=================================")
    print("ANOMALY DETECTION SERVICE PASSED")
    print("=================================")

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )