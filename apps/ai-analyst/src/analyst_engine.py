from analytical_query_service import AnalyticalQueryService
from intent_interpreter import IntentInterpreter


class AnalystEngine:
    """
    End-to-end analytical engine for the Flowmart AI Analyst.

    Converts a natural-language question into a semantic intent,
    executes the corresponding analytical query, and returns the
    structured result.
    """

    def __init__(self):
        self.interpreter = IntentInterpreter()
        self.query_service = AnalyticalQueryService()

    def ask(self, question):
        """
        Answer an analytical question.

        Pipeline:

            Question
                ↓
            Intent
                ↓
            Semantic Query
                ↓
            Trino
                ↓
            Structured Result
        """

        intent = self.interpreter.interpret(
            question
        )

        response = self.query_service.query(
            metrics=intent.metrics,
            dimensions=intent.dimensions,
            filters=intent.filters,
        )

        return {
            "question": question,
            "intent": intent.to_dict(),
            "sql": response["sql"],
            "result": response["result"],
        }


def run_tests():
    """
    Verify the complete deterministic analyst pipeline.
    """

    engine = AnalystEngine()

    print(
        "FLOWMART ANALYST ENGINE"
    )
    print(
        "======================="
    )

    print(
        "\nTest 1 — Natural Language → Revenue"
    )

    response = engine.ask(
        "How much revenue did we make?"
    )

    print(
        "\nQuestion:"
    )
    print(
        response["question"]
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
        response["result"]
    )

    assert response["intent"]["metrics"] == [
        "total_revenue"
    ]

    assert response["result"]["row_count"] == 1

    assert response["result"]["rows"][0][
        "column_1"
    ] == "4967781.58"

    print(
        "[PASS] Revenue question completed end-to-end."
    )

    print(
        "\nTest 2 — Natural Language → Completed Orders"
    )

    response = engine.ask(
        "How many completed orders do we have?"
    )

    print(
        "\nQuestion:"
    )
    print(
        response["question"]
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
        response["result"]
    )

    assert response["intent"]["metrics"] == [
        "order_count"
    ]

    assert response["intent"]["filters"] == {
        "status": "completed"
    }

    assert response["result"]["row_count"] == 1

    assert response["result"]["rows"][0][
        "column_1"
    ] == "3245"

    print(
        "[PASS] Completed-order question completed end-to-end."
    )

    print(
        "\nTest 3 — Natural Language → Revenue by Date"
    )

    response = engine.ask(
        "Show me revenue by date."
    )

    print(
        "\nQuestion:"
    )
    print(
        response["question"]
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
        response["result"]
    )

    assert response["intent"]["metrics"] == [
        "total_revenue"
    ]

    assert response["intent"]["dimensions"] == [
        "order_date"
    ]

    assert response["result"]["row_count"] >= 1

    print(
        "[PASS] Revenue-by-date question completed end-to-end."
    )

    print(
        "\nTest 4 — Natural Language → Orders by Status"
    )

    response = engine.ask(
        "Show order count by status."
    )

    print(
        "\nQuestion:"
    )
    print(
        response["question"]
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
        response["result"]
    )

    assert response["intent"]["metrics"] == [
        "order_count"
    ]

    assert response["intent"]["dimensions"] == [
        "status"
    ]

    assert response["result"]["row_count"] == 5

    print(
        "[PASS] Orders-by-status question completed end-to-end."
    )

    print(
        "\nTest 5 — Unknown Question"
    )

    try:
        engine.ask(
            "What is the moon doing to our warehouse?"
        )

        print(
            "[FAIL] Unknown question was accepted."
        )

        return False

    except ValueError:
        print(
            "[PASS] Unknown question rejected safely."
        )

    print(
        "\n======================="
    )
    print(
        "ANALYST ENGINE PASSED"
    )
    print(
        "======================="
    )

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )