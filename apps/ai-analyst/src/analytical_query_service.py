from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TOOLS_ROOT = Path(__file__).resolve().parent / "tools"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))


from semantic_query_builder import SemanticQueryBuilder
from trino_tool import TrinoQueryTool


class AnalyticalQueryService:
    """
    Connects the Flowmart semantic query builder to the
    read-only Trino query tool.

    The service returns semantically named result columns
    instead of generic column_1, column_2 names.
    """

    def __init__(self):
        self.query_builder = SemanticQueryBuilder()
        self.trino = TrinoQueryTool()

    def query(
        self,
        metrics,
        dimensions=None,
        filters=None,
    ):
        """
        Build and execute a semantic analytical query.

        The output columns follow the same semantic order
        used by the query builder:

            dimensions + metrics
        """

        dimensions = dimensions or []
        filters = filters or {}

        sql = self.query_builder.build(
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
        )

        expected_columns = (
            list(dimensions)
            + list(metrics)
        )

        result = self.trino.execute_with_columns(
            sql,
            expected_columns,
        )

        return {
            "sql": sql,
            "metrics": list(metrics),
            "dimensions": list(dimensions),
            "filters": dict(filters),
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["row_count"],
        }


def run_tests():
    """
    Verify end-to-end semantic query execution and
    semantic result column names.
    """

    service = AnalyticalQueryService()

    print(
        "FLOWMART ANALYTICAL QUERY SERVICE"
    )
    print(
        "================================="
    )

    print(
        "\nTest 1 — Total Revenue"
    )

    response = service.query(
        metrics=[
            "total_revenue"
        ]
    )

    print(
        "\nGenerated SQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nSemantic Result:"
    )
    print(
        response
    )

    assert response["columns"] == [
        "total_revenue"
    ]

    assert response["rows"] == [
        {
            "total_revenue": "4967781.58"
        }
    ]

    assert response["row_count"] == 1

    print(
        "[PASS] Total revenue returned with semantic column name."
    )

    print(
        "\nTest 2 — Revenue by Date"
    )

    response = service.query(
        metrics=[
            "total_revenue"
        ],
        dimensions=[
            "order_date"
        ],
    )

    print(
        "\nGenerated SQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nSemantic Result:"
    )
    print(
        response
    )

    assert response["columns"] == [
        "order_date",
        "total_revenue",
    ]

    assert response["rows"][0][
        "order_date"
    ] == "2026-09-02"

    assert response["rows"][0][
        "total_revenue"
    ] == "4967781.58"

    print(
        "[PASS] Revenue-by-date returned with semantic columns."
    )

    print(
        "\nTest 3 — Orders by Status"
    )

    response = service.query(
        metrics=[
            "order_count"
        ],
        dimensions=[
            "status"
        ],
    )

    print(
        "\nGenerated SQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nSemantic Result:"
    )
    print(
        response
    )

    assert response["columns"] == [
        "status",
        "order_count",
    ]

    assert response["row_count"] == 5

    statuses = {
        row["status"]
        for row in response["rows"]
    }

    assert statuses == {
        "pending",
        "shipped",
        "completed",
        "cancelled",
        "refunded",
    }

    print(
        "[PASS] Orders-by-status returned with semantic columns."
    )

    print(
        "\nTest 4 — Filtered Orders"
    )

    response = service.query(
        metrics=[
            "order_count"
        ],
        filters={
            "status": "completed"
        },
    )

    print(
        "\nGenerated SQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nSemantic Result:"
    )
    print(
        response
    )

    assert response["columns"] == [
        "order_count"
    ]

    assert response["rows"] == [
        {
            "order_count": "3245"
        }
    ]

    print(
        "[PASS] Filtered query returned with semantic column name."
    )

    print(
        "\nTest 5 — Multiple Metrics"
    )

    response = service.query(
        metrics=[
            "order_count",
            "total_revenue",
            "average_order_value",
        ]
    )

    print(
        "\nGenerated SQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nSemantic Result:"
    )
    print(
        response
    )

    assert response["columns"] == [
        "order_count",
        "total_revenue",
        "average_order_value",
    ]

    assert response["row_count"] == 1

    assert response["rows"][0][
        "order_count"
    ] == "5015"

    assert response["rows"][0][
        "total_revenue"
    ] == "4967781.58"

    assert response["rows"][0][
        "average_order_value"
    ] == "990.58"

    print(
        "[PASS] Multiple metrics returned with semantic names."
    )

    print(
        "\n================================="
    )
    print(
        "ANALYTICAL QUERY SERVICE PASSED"
    )
    print(
        "================================="
    )

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )