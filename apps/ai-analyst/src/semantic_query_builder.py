from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from semantic.registry import SemanticRegistry


class SemanticQueryBuilder:
    """
    Builds read-only analytical SQL from Flowmart semantic definitions.

    The query builder does not invent business logic. It uses the
    metric and dimension definitions from the semantic registry.
    """

    def __init__(self):
        self.registry = SemanticRegistry()

    def _get_metric(self, metric_name):
        metric = self.registry.get_metric(metric_name)

        if metric is None:
            raise ValueError(
                f"Unknown metric: {metric_name}"
            )

        return metric

    def _get_dimension(self, dimension_name):
        dimension = self.registry.get_dimension(
            dimension_name
        )

        if dimension is None:
            raise ValueError(
                f"Unknown dimension: {dimension_name}"
            )

        return dimension

    def _dimension_expression(self, dimension):
        """
        Return the SQL expression associated with a dimension.
        """

        if dimension.get("column"):
            return dimension["column"]

        if dimension.get("expression"):
            return dimension["expression"]

        raise ValueError(
            f"Dimension '{dimension.get('name')}' "
            "has no SQL expression."
        )

    def build(
        self,
        metrics,
        dimensions=None,
        filters=None,
    ):
        """
        Build a SELECT query from semantic definitions.

        Parameters
        ----------
        metrics:
            List of semantic metric names.

        dimensions:
            Optional list of semantic dimension names.

        filters:
            Optional dictionary mapping dimension names
            to values.

        Returns
        -------
        str
            Read-only SQL query.
        """

        if not metrics:
            raise ValueError(
                "At least one metric is required."
            )

        dimensions = dimensions or []
        filters = filters or {}

        metric_definitions = [
            self._get_metric(name)
            for name in metrics
        ]

        dimension_definitions = [
            self._get_dimension(name)
            for name in dimensions
        ]

        select_parts = []

        for dimension in dimension_definitions:
            expression = self._dimension_expression(
                dimension
            )

            select_parts.append(
                f"{expression} AS {dimension['name']}"
            )

        for metric in metric_definitions:
            expression = metric["expression"]

            select_parts.append(
                f"{expression} AS {metric['name']}"
            )

        sql = "SELECT\n    "
        sql += ",\n    ".join(select_parts)

        sql += "\nFROM orders"

        where_parts = []

        for dimension_name, value in filters.items():
            dimension = self._get_dimension(
                dimension_name
            )

            expression = self._dimension_expression(
                dimension
            )

            if isinstance(value, (list, tuple)):
                escaped_values = []

                for item in value:
                    escaped_values.append(
                        self._escape_value(item)
                    )

                where_parts.append(
                    f"{expression} IN "
                    f"({', '.join(escaped_values)})"
                )

            else:
                where_parts.append(
                    f"{expression} = "
                    f"{self._escape_value(value)}"
                )

        if where_parts:
            sql += "\nWHERE "
            sql += "\n  AND ".join(where_parts)

        if dimension_definitions:
            group_by = []

            for dimension in dimension_definitions:
                group_by.append(
                    self._dimension_expression(
                        dimension
                    )
                )

            sql += "\nGROUP BY "
            sql += ", ".join(group_by)

        sql += ";"

        return sql

    @staticmethod
    def _escape_value(value):
        """
        Safely escape a scalar SQL value.
        """

        if value is None:
            return "NULL"

        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"

        if isinstance(value, (int, float)):
            return str(value)

        escaped = str(value).replace(
            "'",
            "''"
        )

        return f"'{escaped}'"


def run_tests():
    """
    Verify semantic SQL generation.
    """

    builder = SemanticQueryBuilder()

    print(
        "FLOWMART SEMANTIC QUERY BUILDER"
    )
    print(
        "================================"
    )

    print("\nTest 1 — Total Revenue")

    sql = builder.build(
        metrics=[
            "total_revenue"
        ]
    )

    print(sql)

    assert (
        "SUM(total_amount) AS total_revenue"
        in sql
    )

    print("[PASS] Total revenue query generated.")

    print("\nTest 2 — Revenue by Date")

    sql = builder.build(
        metrics=[
            "total_revenue"
        ],
        dimensions=[
            "order_date"
        ],
    )

    print(sql)

    assert (
        "CAST(created_at AS DATE) AS order_date"
        in sql
    )

    assert (
        "GROUP BY CAST(created_at AS DATE)"
        in sql
    )

    print(
        "[PASS] Revenue-by-date query generated."
    )

    print("\nTest 3 — Orders by Status")

    sql = builder.build(
        metrics=[
            "order_count"
        ],
        dimensions=[
            "status"
        ],
    )

    print(sql)

    assert (
        "COUNT(order_id) AS order_count"
        in sql
    )

    assert (
        "status AS status"
        in sql
    )

    assert (
        "GROUP BY status"
        in sql
    )

    print(
        "[PASS] Orders-by-status query generated."
    )

    print("\nTest 4 — Filter")

    sql = builder.build(
        metrics=[
            "order_count"
        ],
        dimensions=[
            "status"
        ],
        filters={
            "status": "completed"
        },
    )

    print(sql)

    assert (
        "WHERE status = 'completed'"
        in sql
    )

    print(
        "[PASS] Filtered query generated."
    )

    print("\nTest 5 — Unknown Metric")

    try:
        builder.build(
            metrics=[
                "fake_metric"
            ]
        )

        print(
            "[FAIL] Unknown metric was accepted."
        )
        return False

    except ValueError:
        print(
            "[PASS] Unknown metric rejected."
        )

    print("\nTest 6 — Unknown Dimension")

    try:
        builder.build(
            metrics=[
                "total_revenue"
            ],
            dimensions=[
                "fake_dimension"
            ],
        )

        print(
            "[FAIL] Unknown dimension was accepted."
        )
        return False

    except ValueError:
        print(
            "[PASS] Unknown dimension rejected."
        )

    print("\n================================")
    print(
        "SEMANTIC QUERY BUILDER PASSED"
    )
    print("================================")

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )