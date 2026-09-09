from pathlib import Path
import argparse
import csv
import io
import re
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[4]


class TrinoQueryTool:
    """
    Read-only query tool for the Flowmart AI Analyst.

    The tool executes analytical SQL against Trino while enforcing
    safety rules so the AI Analyst cannot modify the warehouse.
    """

    FORBIDDEN_KEYWORDS = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "MERGE",
        "CALL",
        "GRANT",
        "REVOKE",
    }

    ALLOWED_STARTS = (
        "SELECT ",
        "WITH ",
        "SHOW ",
        "DESCRIBE ",
        "EXPLAIN ",
    )

    def __init__(
        self,
        container_name="atlas-trino",
        server="http://localhost:8080",
        user="flowmart",
        catalog="iceberg",
        schema="atlas",
    ):
        self.container_name = container_name
        self.server = server
        self.user = user
        self.catalog = catalog
        self.schema = schema

    def _validate_query(self, sql):
        """
        Validate that the query is read-only.
        """

        if not sql or not sql.strip():
            raise ValueError(
                "SQL query cannot be empty."
            )

        normalized = " ".join(
            sql.strip().upper().split()
        )

        if not normalized.startswith(
            self.ALLOWED_STARTS
        ):
            raise ValueError(
                "Only read-only SELECT, WITH, SHOW, DESCRIBE, "
                "and EXPLAIN queries are allowed."
            )

        for keyword in self.FORBIDDEN_KEYWORDS:
            pattern = rf"\b{keyword}\b"

            if re.search(
                pattern,
                normalized,
            ):
                raise ValueError(
                    f"Forbidden SQL keyword detected: {keyword}"
                )

        if ";" in normalized.rstrip(";"):
            raise ValueError(
                "Multiple SQL statements are not allowed."
            )

    def execute(self, sql):
        """
        Execute a validated read-only SQL query through Trino.

        Returns a structured result containing:
        - columns
        - rows
        - row_count
        - query
        """

        self._validate_query(sql)

        command = [
            "docker",
            "exec",
            self.container_name,
            "trino",
            "--server",
            self.server,
            "--user",
            self.user,
            "--catalog",
            self.catalog,
            "--schema",
            self.schema,
            "--execute",
            sql,
        ]

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if result.returncode != 0:
            error = result.stderr.strip()

            if not error:
                error = "Trino query failed."

            raise RuntimeError(error)

        output = result.stdout.strip()

        if not output:
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "query": sql.strip(),
            }

        reader = csv.reader(
            io.StringIO(output)
        )

        raw_rows = list(reader)

        if not raw_rows:
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "query": sql.strip(),
            }

        column_count = len(
            raw_rows[0]
        )

        columns = [
            f"column_{index + 1}"
            for index in range(column_count)
        ]

        rows = [
            dict(zip(columns, row))
            for row in raw_rows
        ]

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "query": sql.strip(),
        }

    def execute_with_columns(
        self,
        sql,
        columns,
    ):
        """
        Execute a query when the caller already knows the
        expected semantic column names.

        The Trino CLI used by Flowmart does not currently return
        column headers, so the semantic layer supplies the names.
        """

        result = self.execute(sql)

        if len(columns) != len(
            result["columns"]
        ):
            raise ValueError(
                "Provided column count does not match "
                "the Trino result."
            )

        result["columns"] = list(columns)

        result["rows"] = [
            dict(
                zip(
                    columns,
                    row.values(),
                )
            )
            for row in result["rows"]
        ]

        return result


def run_static_validation_tests():
    """
    Run tests that do not require Docker or a live Trino instance.

    These tests are suitable for GitHub Actions and other CI
    environments where Flowmart infrastructure is not running.
    """

    print(
        "FLOWMART TRINO TOOL — STATIC VALIDATION"
    )
    print(
        "======================================="
    )

    tool = TrinoQueryTool()

    passed = 0
    total = 0

    print()
    print("Read-only query validation:")

    valid_queries = [
        """
        SELECT
            COUNT(*) AS order_count,
            SUM(total_amount) AS total_revenue
        FROM orders
        """,
        """
        SELECT
            CAST(created_at AS DATE) AS order_date,
            SUM(total_amount) AS total_revenue
        FROM orders
        GROUP BY CAST(created_at AS DATE)
        """,
        """
        SELECT
            updated_at,
            COUNT(*) AS order_count
        FROM orders
        GROUP BY updated_at
        LIMIT 5
        """,
        """
        WITH recent_orders AS (
            SELECT order_id, total_amount
            FROM orders
        )
        SELECT
            COUNT(*) AS order_count
        FROM recent_orders
        """,
    ]

    for query in valid_queries:
        total += 1

        try:
            tool._validate_query(query)

            print(
                "[PASS] Analytical query accepted."
            )

            passed += 1

        except ValueError as error:
            print(
                "[FAIL] Legitimate query rejected:"
            )

            print(
                f"       {error}"
            )

    print()
    print("Destructive query protection:")

    blocked_queries = [
        "DROP TABLE orders",
        "DELETE FROM orders",
        "UPDATE orders SET status = 'cancelled'",
        "CREATE TABLE evil AS SELECT * FROM orders",
        "INSERT INTO orders SELECT * FROM orders",
        "ALTER TABLE orders DROP COLUMN status",
        "TRUNCATE TABLE orders",
        "MERGE INTO orders USING orders ON orders.order_id = orders.order_id",
        "CALL system.runtime.kill_query('123')",
        "GRANT SELECT ON orders TO evil_user",
        "REVOKE SELECT ON orders FROM evil_user",
    ]

    for query in blocked_queries:
        total += 1

        try:
            tool._validate_query(query)

            print(
                f"[FAIL] Query was not blocked: {query}"
            )

        except ValueError:
            print(
                f"[PASS] Blocked: {query}"
            )

            passed += 1

    print()
    print(
        f"Static validation tests: "
        f"{passed}/{total} passed"
    )

    if passed == total:
        print(
            "TRINO TOOL STATIC VALIDATION PASSED"
        )
        return True

    print(
        "TRINO TOOL STATIC VALIDATION FAILED"
    )

    return False


def run_data_test():
    """
    Verify that the tool returns structured analytical data.

    This is an integration test and requires the local
    atlas-trino Docker container.
    """

    tool = TrinoQueryTool()

    result = tool.execute(
        """
        SELECT
            COUNT(*) AS order_count,
            SUM(total_amount) AS total_revenue
        FROM orders
        """
    )

    print(
        "FLOWMART TRINO TOOL — STRUCTURED RESULT"
    )
    print(
        "========================================"
    )

    print(
        f"Columns:   {result['columns']}"
    )

    print(
        f"Rows:      {result['rows']}"
    )

    print(
        f"Row count: {result['row_count']}"
    )

    if result["row_count"] != 1:
        print(
            "STRUCTURED RESULT TEST FAILED"
        )
        return False

    if len(result["columns"]) != 2:
        print(
            "STRUCTURED RESULT TEST FAILED"
        )
        return False

    print()
    print(
        "STRUCTURED RESULT TEST PASSED"
    )

    return True


def run_semantic_column_test():
    """
    Verify that generic Trino columns can be mapped to
    semantic column names.

    This is an integration test and requires the local
    atlas-trino Docker container.
    """

    tool = TrinoQueryTool()

    result = tool.execute_with_columns(
        """
        SELECT
            status,
            COUNT(order_id)
        FROM orders
        GROUP BY status
        """,
        [
            "status",
            "order_count",
        ],
    )

    print()
    print(
        "FLOWMART TRINO TOOL — SEMANTIC COLUMN TEST"
    )
    print(
        "=========================================="
    )

    print(
        f"Columns:   {result['columns']}"
    )

    print(
        f"Rows:      {result['rows']}"
    )

    print(
        f"Row count: {result['row_count']}"
    )

    assert result["columns"] == [
        "status",
        "order_count",
    ]

    assert result["row_count"] == 5

    assert all(
        "status" in row
        and "order_count" in row
        for row in result["rows"]
    )

    print(
        "[PASS] Semantic column mapping works."
    )

    print(
        "SEMANTIC COLUMN TEST PASSED"
    )

    return True


def run_read_only_query_tests():
    """
    Verify that legitimate analytical queries execute correctly
    against the real Trino environment.

    This is an integration test and requires the local
    atlas-trino Docker container.
    """

    tool = TrinoQueryTool()

    queries = [
        """
        SELECT
            CAST(created_at AS DATE) AS order_date,
            SUM(total_amount) AS total_revenue
        FROM orders
        GROUP BY CAST(created_at AS DATE)
        """,
        """
        SELECT
            updated_at,
            COUNT(*) AS order_count
        FROM orders
        GROUP BY updated_at
        LIMIT 5
        """,
    ]

    print()
    print(
        "FLOWMART TRINO TOOL — READ-ONLY QUERY TEST"
    )
    print(
        "=========================================="
    )

    passed = 0

    for query in queries:
        try:
            result = tool.execute(query)

            print(
                "[PASS] Analytical query accepted."
            )

            print(
                f"       Rows returned: "
                f"{result['row_count']}"
            )

            passed += 1

        except Exception as error:
            print(
                "[FAIL] Legitimate query rejected:"
            )

            print(
                f"       {error}"
            )

    print()

    print(
        f"Read-only tests: "
        f"{passed}/{len(queries)} passed"
    )

    if passed == len(queries):
        print(
            "READ-ONLY QUERY TEST PASSED"
        )
        return True

    print(
        "READ-ONLY QUERY TEST FAILED"
    )

    return False


def run_integration_tests():
    """
    Run the full Trino integration suite.

    Requires the local atlas-trino Docker container.
    """

    print(
        "FLOWMART TRINO TOOL — INTEGRATION MODE"
    )
    print(
        "======================================"
    )

    data_test = run_data_test()

    semantic_test = run_semantic_column_test()

    readonly_test = run_read_only_query_tests()

    print()
    print(
        "========================================"
    )

    if (
        data_test
        and semantic_test
        and readonly_test
    ):
        print(
            "FLOWMART TRINO INTEGRATION PASSED"
        )

        print(
            "========================================"
        )

        return True

    print(
        "FLOWMART TRINO INTEGRATION FAILED"
    )

    print(
        "========================================"
    )

    return False


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Validate the Flowmart read-only Trino query tool."
        )
    )

    parser.add_argument(
        "--integration",
        action="store_true",
        help=(
            "Run integration tests against the local "
            "atlas-trino Docker container."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.integration:
        success = run_integration_tests()
    else:
        success = run_static_validation_tests()

    raise SystemExit(
        0 if success else 1
    )