from pathlib import Path
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


def run_data_test():
    """
    Verify that the tool returns structured analytical data.
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


def run_security_tests():
    """
    Verify that destructive SQL statements are rejected
    before reaching Trino.
    """

    tool = TrinoQueryTool()

    blocked_queries = [
        "DROP TABLE orders",
        "DELETE FROM orders",
        "UPDATE orders SET status = 'cancelled'",
        "CREATE TABLE evil AS SELECT * FROM orders",
        "INSERT INTO orders SELECT * FROM orders",
        "ALTER TABLE orders DROP COLUMN status",
        "TRUNCATE TABLE orders",
        "MERGE INTO orders USING orders ON orders.order_id = orders.order_id",
    ]

    print()
    print(
        "FLOWMART TRINO TOOL — SECURITY TEST"
    )
    print(
        "==================================="
    )

    passed = 0

    for query in blocked_queries:
        try:
            tool.execute(query)

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
        f"Security tests: "
        f"{passed}/{len(blocked_queries)} passed"
    )

    if passed == len(blocked_queries):
        print(
            "TRINO TOOL SECURITY TEST PASSED"
        )
        return True

    print(
        "TRINO TOOL SECURITY TEST FAILED"
    )

    return False


def run_read_only_query_tests():
    """
    Verify that legitimate analytical queries containing
    words such as CREATED_AT are accepted.
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


if __name__ == "__main__":
    data_test = run_data_test()

    semantic_test = run_semantic_column_test()

    security_test = run_security_tests()

    readonly_test = run_read_only_query_tests()

    print()
    print(
        "========================================"
    )

    if (
        data_test
        and semantic_test
        and security_test
        and readonly_test
    ):
        print(
            "FLOWMART TRINO QUERY TOOL PASSED"
        )

        print(
            "========================================"
        )

        raise SystemExit(0)

    print(
        "FLOWMART TRINO QUERY TOOL FAILED"
    )

    print(
        "========================================"
    )

    raise SystemExit(1)