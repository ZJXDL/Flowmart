
from pathlib import Path
import argparse
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from analyst_answer_generator import AnalystAnswerGenerator
from analytical_query_service import AnalyticalQueryService
from llm_client import LLMClient
from llm_intent_interpreter import LLMIntentInterpreter
from semantic.registry import SemanticRegistry


class LLMAnalystEngine:
    """
    End-to-end Flowmart AI Analyst engine.

    Pipeline:

        Natural-language question
                ↓
        LLM Intent Interpreter
                ↓
        Semantic validation
                ↓
        AnalystIntent
                ↓
        Semantic Query Builder
                ↓
        Read-only Trino
                ↓
        Trusted analytical result
                ↓
        Compact presentation result
                ↓
        LLM Answer Generator
                ↓
        Numeric claim validation
                ↓
        Natural-language answer

    IMPORTANT:

    The complete Trino result is always preserved and returned.

    For large result sets, only a bounded presentation view is sent
    to the answer-generation LLM.

    The presentation view is deterministic:

        - The complete analytical result is preserved.
        - Small results are sent completely.
        - Large results are reduced to the top N rows according
          to the first metric column.
        - The answer LLM is explicitly told that the result is
          a top-N presentation view rather than the complete result.

    This prevents large analytical result sets from exceeding
    LLM provider token limits while making the narrated preview
    analytically useful.
    """

    MAX_LLM_PREVIEW_ROWS = 10

    def __init__(
        self,
        llm_client,
        semantic_registry=None,
        answer_llm_client=None,
    ):
        self.registry = (
            semantic_registry
            or SemanticRegistry()
        )

        self.interpreter = (
            LLMIntentInterpreter(
                llm_client=llm_client,
                semantic_registry=self.registry,
            )
        )

        self.query_service = (
            AnalyticalQueryService()
        )

        self.answer_generator = (
            AnalystAnswerGenerator(
                llm_client=(
                    answer_llm_client
                    or llm_client
                )
            )
        )

    @staticmethod
    def _find_preview_metric_column(
        columns,
        rows,
    ):
        """
        Identify the first numeric metric column that can be used
        to rank a large analytical result.
        """

        if not isinstance(columns, list):
            return None

        if not isinstance(rows, list):
            return None

        for column in columns:

            for row in rows:

                if not isinstance(row, dict):
                    continue

                value = row.get(column)

                if value is None:
                    continue

                try:
                    float(
                        str(value)
                        .replace(",", "")
                    )

                    return column

                except (ValueError, TypeError):
                    continue

        return None

    @staticmethod
    def _numeric_sort_value(value):
        """
        Convert a result value into a numeric value suitable
        for deterministic descending ranking.
        """

        if value is None:
            return None

        try:
            return float(
                str(value)
                .replace(",", "")
            )

        except (ValueError, TypeError):
            return None

    def _prepare_result_for_llm(
        self,
        columns,
        rows,
        row_count,
    ):
        """
        Prepare a bounded presentation result for the answer LLM.

        The complete analytical result remains untouched.

        For small result sets, all rows are sent.

        For large result sets, the top
        MAX_LLM_PREVIEW_ROWS rows are selected according to
        the first numeric metric column.
        """

        if row_count <= self.MAX_LLM_PREVIEW_ROWS:
            return {
                "columns": columns,
                "rows": rows,
                "row_count": row_count,
                "is_preview": False,
                "preview_row_count": row_count,
                "preview_type": "complete",
            }

        metric_column = (
            self._find_preview_metric_column(
                columns=columns,
                rows=rows,
            )
        )

        if metric_column is not None:

            sortable_rows = []

            for index, row in enumerate(rows):

                if not isinstance(row, dict):
                    continue

                numeric_value = (
                    self._numeric_sort_value(
                        row.get(metric_column)
                    )
                )

                if numeric_value is None:
                    continue

                sortable_rows.append(
                    (
                        numeric_value,
                        index,
                        row,
                    )
                )

            sortable_rows.sort(
                key=lambda item: (
                    -item[0],
                    item[1],
                )
            )

            preview_rows = [
                item[2]
                for item in sortable_rows[
                    :self.MAX_LLM_PREVIEW_ROWS
                ]
            ]

            return {
                "columns": columns,
                "rows": preview_rows,
                "row_count": row_count,
                "is_preview": True,
                "preview_row_count": len(
                    preview_rows
                ),
                "omitted_row_count": (
                    row_count
                    - len(preview_rows)
                ),
                "preview_type": "top_n",
                "preview_limit": (
                    self.MAX_LLM_PREVIEW_ROWS
                ),
                "ranking_column": metric_column,
                "ranking_order": "descending",
            }

        preview_rows = rows[
            :self.MAX_LLM_PREVIEW_ROWS
        ]

        return {
            "columns": columns,
            "rows": preview_rows,
            "row_count": row_count,
            "is_preview": True,
            "preview_row_count": len(
                preview_rows
            ),
            "omitted_row_count": (
                row_count
                - len(preview_rows)
            ),
            "preview_type": "bounded_preview",
            "preview_limit": (
                self.MAX_LLM_PREVIEW_ROWS
            ),
        }

    def ask(self, question):
        """
        Execute the complete AI Analyst pipeline.

        The LLM interprets the question.
        The semantic layer validates that interpretation.
        The query service generates deterministic SQL.
        Trino executes the read-only query.
        The complete trusted result is preserved.
        A bounded presentation result is sent to the answer LLM.
        """

        intent = self.interpreter.interpret(
            question
        )

        response = self.query_service.query(
            metrics=intent.metrics,
            dimensions=intent.dimensions,
            filters=intent.filters,
        )

        complete_result = {
            "columns": response["columns"],
            "rows": response["rows"],
            "row_count": response["row_count"],
        }

        llm_result = (
            self._prepare_result_for_llm(
                columns=response["columns"],
                rows=response["rows"],
                row_count=response["row_count"],
            )
        )

        answer = self.answer_generator.generate(
            question=question,
            intent=intent.to_dict(),
            sql=response["sql"],
            result=llm_result,
        )

        return {
            "question": question,
            "intent": intent.to_dict(),
            "sql": response["sql"],
            "metrics": response["metrics"],
            "dimensions": response["dimensions"],
            "filters": response["filters"],
            "columns": complete_result["columns"],
            "rows": complete_result["rows"],
            "row_count": complete_result["row_count"],
            "answer": answer,
        }


class MockCombinedLLMClient(LLMClient):
    """
    Deterministic mock LLM capable of performing both:

        1. Intent interpretation
        2. Answer generation

    Used for development and CI-safe tests.
    """

    def __init__(
        self,
        intent_responses=None,
        answer_responses=None,
    ):
        self.intent_responses = (
            intent_responses or {}
        )

        self.answer_responses = (
            answer_responses or {}
        )

    def generate(
        self,
        system_prompt,
        user_prompt,
    ):
        """
        Return a deterministic response for either:

            - intent interpretation
            - analytical answer generation
        """

        if '"trusted_result"' in user_prompt:

            for question, response in (
                self.answer_responses.items()
            ):
                if (
                    f'"question": "{question}"'
                    in user_prompt
                ):
                    return response

            raise ValueError(
                "No mock answer response configured."
            )

        for question, response in (
            self.intent_responses.items()
        ):
            if question in user_prompt:
                return response

        raise ValueError(
            "No mock intent response configured."
        )


def build_test_engine():
    """
    Build a deterministic engine for tests that do not require
    live LLM or Trino infrastructure.
    """

    intent_responses = {
        "How much revenue did we make?":
            '{"metrics":["total_revenue"],'
            '"dimensions":[],"filters":{}}',

        "How many completed orders do we have?":
            '{"metrics":["order_count"],'
            '"dimensions":["status"],'
            '"filters":{"status":"completed"}}',

        "Show revenue by status.":
            '{"metrics":["total_revenue"],'
            '"dimensions":["status"],'
            '"filters":{}}',
    }

    answer_responses = {
        "How much revenue did we make?":
            "Flowmart generated "
            "$4,967,781.58 in total revenue.",

        "How many completed orders do we have?":
            "Flowmart currently has "
            "3,245 completed orders.",

        "Show revenue by status.":
            "Completed orders generated the "
            "highest revenue at $3,243,235.14, "
            "while cancelled orders generated "
            "$419,671.74.",
    }

    client = MockCombinedLLMClient(
        intent_responses=intent_responses,
        answer_responses=answer_responses,
    )

    return (
        LLMAnalystEngine(
            llm_client=client
        ),
        client,
    )


def run_static_tests():
    """
    Run deterministic tests that do not require Docker, Trino,
    or external LLM APIs.

    These tests are safe for GitHub Actions.
    """

    engine, client = build_test_engine()

    print(
        "FLOWMART AI ANALYST — STATIC TESTS"
    )
    print(
        "================================="
    )

    # =============================================================
    # TEST 1 — HALLUCINATION PROTECTION
    # =============================================================

    print(
        "\nTest 1 — Hallucination Protection"
    )

    hallucinating_client = (
        MockCombinedLLMClient(
            intent_responses={
                "What is our profit margin?":
                    '{"metrics":["profit_margin"],'
                    '"dimensions":[],"filters":{}}'
            },
            answer_responses={},
        )
    )

    hallucination_interpreter = (
        LLMIntentInterpreter(
            llm_client=hallucinating_client,
            semantic_registry=(
                SemanticRegistry()
            ),
        )
    )

    try:
        hallucination_interpreter.interpret(
            "What is our profit margin?"
        )

        print(
            "[FAIL] Hallucinated intent was accepted."
        )

        return False

    except ValueError as error:
        print(
            "[PASS] Hallucinated intent blocked:"
        )
        print(
            error
        )

    # =============================================================
    # TEST 2 — MOCK REQUEST ROUTING
    # =============================================================

    print(
        "\nTest 2 — Mock Request Routing"
    )

    routing_client = (
        MockCombinedLLMClient(
            intent_responses={
                "ROUTING INTENT TEST":
                    '{"metrics":["total_revenue"],'
                    '"dimensions":[],"filters":{}}'
            },
            answer_responses={
                "ROUTING ANSWER TEST":
                    "Revenue was $4,967,781.58."
            },
        )
    )

    intent_result = routing_client.generate(
        system_prompt="Any intent prompt.",
        user_prompt=(
            "Interpret this question: "
            "ROUTING INTENT TEST"
        ),
    )

    assert (
        intent_result
        == '{"metrics":["total_revenue"],'
        '"dimensions":[],"filters":{}}'
    )

    answer_result = routing_client.generate(
        system_prompt="Any answer prompt.",
        user_prompt=(
            '{'
            '"question": "ROUTING ANSWER TEST",'
            '"intent": {},'
            '"trusted_result": {'
            '"columns": ["total_revenue"],'
            '}'
            '}'
        ),
    )

    assert (
        answer_result
        == "Revenue was $4,967,781.58."
    )

    print(
        "[PASS] Mock intent/answer routing is stable."
    )

    # =============================================================
    # TEST 3 — LARGE RESULT PRESENTATION BOUNDARY
    # =============================================================

    print(
        "\nTest 3 — Large Result Presentation Boundary"
    )

    large_rows = []

    for index in range(25):
        large_rows.append(
            {
                "customer_id":
                    f"customer-{index}",
                "total_revenue":
                    str(index * 100),
            }
        )

    compact_result = (
        engine._prepare_result_for_llm(
            columns=[
                "customer_id",
                "total_revenue",
            ],
            rows=large_rows,
            row_count=25,
        )
    )

    assert (
        len(compact_result["rows"])
        == 10
    )

    assert (
        compact_result["row_count"]
        == 25
    )

    assert (
        compact_result["is_preview"]
        is True
    )

    assert (
        compact_result["preview_row_count"]
        == 10
    )

    assert (
        compact_result["omitted_row_count"]
        == 15
    )

    assert (
        compact_result["preview_type"]
        == "top_n"
    )

    assert (
        compact_result["ranking_column"]
        == "total_revenue"
    )

    assert (
        compact_result["ranking_order"]
        == "descending"
    )

    expected_revenues = [
        str(index * 100)
        for index in range(24, 14, -1)
    ]

    actual_revenues = [
        row["total_revenue"]
        for row in compact_result["rows"]
    ]

    assert (
        actual_revenues
        == expected_revenues
    )

    assert (
        len(large_rows)
        == 25
    )

    assert (
        large_rows[0]["total_revenue"]
        == "0"
    )

    assert (
        large_rows[-1]["total_revenue"]
        == "2400"
    )

    print(
        "[PASS] Large results are bounded for LLM narration "
        "using deterministic top-N ranking without truncating "
        "the complete analytical result."
    )

    # =============================================================
    # TEST 4 — SMALL RESULT REMAINS COMPLETE
    # =============================================================

    print(
        "\nTest 4 — Small Result Remains Complete"
    )

    small_rows = [
        {
            "status": "completed",
            "total_revenue": "3243235.14",
        },
        {
            "status": "cancelled",
            "total_revenue": "419671.74",
        },
    ]

    compact_result = (
        engine._prepare_result_for_llm(
            columns=[
                "status",
                "total_revenue",
            ],
            rows=small_rows,
            row_count=2,
        )
    )

    assert (
        compact_result["rows"]
        == small_rows
    )

    assert (
        compact_result["row_count"]
        == 2
    )

    assert (
        compact_result["is_preview"]
        is False
    )

    assert (
        compact_result["preview_type"]
        == "complete"
    )

    print(
        "[PASS] Small results remain complete for the answer LLM."
    )

    # =============================================================
    # TEST 5 — TOP-N RANKING WITH DECIMAL VALUES
    # =============================================================

    print(
        "\nTest 5 — Top-N Ranking With Decimal Values"
    )

    decimal_rows = [
        {
            "customer_id": "customer-a",
            "total_revenue": "2549.65",
        },
        {
            "customer_id": "customer-b",
            "total_revenue": "12089.51",
        },
        {
            "customer_id": "customer-c",
            "total_revenue": "3659.85",
        },
        {
            "customer_id": "customer-d",
            "total_revenue": "16784.14",
        },
        {
            "customer_id": "customer-e",
            "total_revenue": "8219.59",
        },
        {
            "customer_id": "customer-f",
            "total_revenue": "11019.44",
        },
        {
            "customer_id": "customer-g",
            "total_revenue": "754.81",
        },
        {
            "customer_id": "customer-h",
            "total_revenue": "16074.36",
        },
        {
            "customer_id": "customer-i",
            "total_revenue": "10269.47",
        },
        {
            "customer_id": "customer-j",
            "total_revenue": "5889.84",
        },
        {
            "customer_id": "customer-k",
            "total_revenue": "684.89",
        },
    ]

    decimal_result = (
        engine._prepare_result_for_llm(
            columns=[
                "customer_id",
                "total_revenue",
            ],
            rows=decimal_rows,
            row_count=11,
        )
    )

    assert (
        decimal_result["preview_type"]
        == "top_n"
    )

    assert (
        decimal_result["ranking_column"]
        == "total_revenue"
    )

    expected_customers = [
        "customer-d",
        "customer-h",
        "customer-b",
        "customer-f",
        "customer-i",
        "customer-e",
        "customer-j",
        "customer-c",
        "customer-a",
        "customer-g",
    ]

    actual_customers = [
        row["customer_id"]
        for row in decimal_result["rows"]
    ]

    assert (
        actual_customers
        == expected_customers
    )

    print(
        "[PASS] Decimal revenue values are ranked correctly "
        "from highest to lowest."
    )

    # =============================================================
    # TEST 6 — NO NUMERIC RANKING COLUMN FALLBACK
    # =============================================================

    print(
        "\nTest 6 — Non-Numeric Result Fallback"
    )

    categorical_rows = [
        {
            "status": "completed",
        },
        {
            "status": "cancelled",
        },
        {
            "status": "refunded",
        },
        {
            "status": "pending",
        },
        {
            "status": "shipped",
        },
        {
            "status": "completed",
        },
        {
            "status": "cancelled",
        },
        {
            "status": "refunded",
        },
        {
            "status": "pending",
        },
        {
            "status": "shipped",
        },
        {
            "status": "completed",
        },
    ]

    categorical_result = (
        engine._prepare_result_for_llm(
            columns=[
                "status",
            ],
            rows=categorical_rows,
            row_count=11,
        )
    )

    assert (
        categorical_result["preview_type"]
        == "bounded_preview"
    )

    assert (
        categorical_result["is_preview"]
        is True
    )

    assert (
        len(categorical_result["rows"])
        == 10
    )

    assert (
        categorical_result["rows"]
        == categorical_rows[:10]
    )

    print(
        "[PASS] Non-numeric results use an honest bounded "
        "preview instead of inventing a ranking."
    )

    print(
        "\n================================="
    )
    print(
        "STATIC AI ANALYST TESTS PASSED"
    )
    print(
        "================================="
    )

    return True


def run_integration_tests():
    """
    Run the complete deterministic end-to-end AI Analyst suite.

    Requires the local atlas-trino Docker container.

    Tests:

        Natural language
            ↓
        Mock LLM intent
            ↓
        Semantic validation
            ↓
        Query builder
            ↓
        Real Trino
            ↓
        Trusted analytical result
            ↓
        Bounded answer result
            ↓
        Mock answer LLM
    """

    engine, _ = build_test_engine()

    print(
        "FLOWMART END-TO-END AI ANALYST — INTEGRATION"
    )
    print(
        "============================================="
    )

    # =============================================================
    # TEST 1 — REVENUE
    # =============================================================

    print(
        "\nTest 1 — Revenue"
    )

    response = engine.ask(
        "How much revenue did we make?"
    )

    print(
        "\nIntent:"
    )
    print(
        response["intent"]
    )

    print(
        "\nSQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nResult:"
    )
    print(
        response["rows"]
    )

    print(
        "\nAI Answer:"
    )
    print(
        response["answer"]
    )

    assert (
        response["intent"]["metrics"]
        == ["total_revenue"]
    )

    assert (
        response["intent"]["dimensions"]
        == []
    )

    assert (
        response["intent"]["filters"]
        == {}
    )

    assert (
        response["columns"]
        == ["total_revenue"]
    )

    assert (
        response["rows"]
        == [
            {
                "total_revenue":
                    "4967781.58"
            }
        ]
    )

    assert (
        response["row_count"]
        == 1
    )

    assert (
        "$4,967,781.58"
        in response["answer"]
    )

    print(
        "[PASS] Complete revenue analysis."
    )

    # =============================================================
    # TEST 2 — COMPLETED ORDERS
    # =============================================================

    print(
        "\nTest 2 — Completed Orders"
    )

    response = engine.ask(
        "How many completed orders do we have?"
    )

    print(
        "\nIntent:"
    )
    print(
        response["intent"]
    )

    print(
        "\nSQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nResult:"
    )
    print(
        response["rows"]
    )

    print(
        "\nAI Answer:"
    )
    print(
        response["answer"]
    )

    assert (
        response["intent"]["metrics"]
        == ["order_count"]
    )

    assert (
        response["intent"]["dimensions"]
        == ["status"]
    )

    assert (
        response["intent"]["filters"]
        == {
            "status": "completed"
        }
    )

    assert (
        response["columns"]
        == [
            "status",
            "order_count",
        ]
    )

    assert (
        response["rows"]
        == [
            {
                "status": "completed",
                "order_count": "3245",
            }
        ]
    )

    assert (
        response["row_count"]
        == 1
    )

    assert (
        "3,245"
        in response["answer"]
    )

    print(
        "[PASS] Completed-order analysis."
    )

    # =============================================================
    # TEST 3 — REVENUE BY STATUS
    # =============================================================

    print(
        "\nTest 3 — Revenue by Status"
    )

    response = engine.ask(
        "Show revenue by status."
    )

    print(
        "\nIntent:"
    )
    print(
        response["intent"]
    )

    print(
        "\nSQL:"
    )
    print(
        response["sql"]
    )

    print(
        "\nResult:"
    )
    print(
        response["rows"]
    )

    print(
        "\nAI Answer:"
    )
    print(
        response["answer"]
    )

    assert (
        response["intent"]["metrics"]
        == ["total_revenue"]
    )

    assert (
        response["intent"]["dimensions"]
        == ["status"]
    )

    assert (
        response["intent"]["filters"]
        == {}
    )

    assert (
        response["columns"]
        == [
            "status",
            "total_revenue",
        ]
    )

    assert (
        response["row_count"]
        == 5
    )

    assert (
        "3,243,235.14"
        in response["answer"]
    )

    assert (
        "419,671.74"
        in response["answer"]
    )

    print(
        "[PASS] Revenue-by-status analysis."
    )

    print(
        "\n============================================="
    )
    print(
        "END-TO-END AI ANALYST INTEGRATION PASSED"
    )
    print(
        "============================================="
    )

    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run Flowmart AI Analyst tests."
        )
    )

    parser.add_argument(
        "--integration",
        action="store_true",
        help=(
            "Run the full end-to-end suite against "
            "the local atlas-trino Docker container."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.integration:
        success = run_integration_tests()
    else:
        success = run_static_tests()

    raise SystemExit(
        0 if success else 1
    )