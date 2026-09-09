from analyst_intent import AnalystIntent


class IntentInterpreter:
    """
    Deterministic natural-language interpreter for the Flowmart
    AI Analyst.

    This component converts common analytical questions into
    structured AnalystIntent objects.

    It is intentionally deterministic during development.
    A future LLM-based interpreter can implement the same
    interface.
    """

    def interpret(self, question):
        """
        Convert a natural-language question into an AnalystIntent.
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        normalized = question.strip().lower()

        # --------------------------------------------------
        # Completed orders
        # --------------------------------------------------

        if (
            "completed orders" in normalized
            or "orders completed" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ],
                filters={
                    "status": "completed"
                },
            )

        # --------------------------------------------------
        # Cancelled orders
        # --------------------------------------------------

        if (
            "cancelled orders" in normalized
            or "canceled orders" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ],
                filters={
                    "status": "cancelled"
                },
            )

        # --------------------------------------------------
        # Refunded orders
        # --------------------------------------------------

        if (
            "refunded orders" in normalized
            or "orders refunded" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ],
                filters={
                    "status": "refunded"
                },
            )

        # --------------------------------------------------
        # Shipped orders
        # --------------------------------------------------

        if (
            "shipped orders" in normalized
            or "orders shipped" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ],
                filters={
                    "status": "shipped"
                },
            )

        # --------------------------------------------------
        # Pending orders
        # --------------------------------------------------

        if (
            "pending orders" in normalized
            or "orders pending" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ],
                filters={
                    "status": "pending"
                },
            )

        # --------------------------------------------------
        # Cancelled order rate
        # --------------------------------------------------

        if (
            "cancelled order rate" in normalized
            or "canceled order rate" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "cancelled_order_rate"
                ]
            )

        # --------------------------------------------------
        # Refunded order rate
        # --------------------------------------------------

        if "refunded order rate" in normalized:
            return AnalystIntent(
                metrics=[
                    "refunded_order_rate"
                ]
            )

        # --------------------------------------------------
        # Average order value
        # --------------------------------------------------

        if (
            "average order value" in normalized
            or "average order" in normalized
            or "aov" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "average_order_value"
                ]
            )

        # --------------------------------------------------
        # Revenue per customer
        # --------------------------------------------------

        if (
            "revenue per customer" in normalized
            or "revenue per user" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "revenue_per_customer"
                ]
            )

        # --------------------------------------------------
        # Customer count
        # --------------------------------------------------

        if (
            "customer count" in normalized
            or "number of customers" in normalized
            or "how many customers" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "customer_count"
                ]
            )

        # --------------------------------------------------
        # Orders by status
        # --------------------------------------------------

        if (
            "orders by status" in normalized
            or "order count by status" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ],
                dimensions=[
                    "status"
                ],
            )

        # --------------------------------------------------
        # Revenue by status
        # --------------------------------------------------

        if (
            "revenue by status" in normalized
            or "sales by status" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "total_revenue"
                ],
                dimensions=[
                    "status"
                ],
            )

        # --------------------------------------------------
        # Revenue by date
        # --------------------------------------------------

        if (
            "revenue by date" in normalized
            or "sales by date" in normalized
            or "daily revenue" in normalized
            or "revenue per day" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "total_revenue"
                ],
                dimensions=[
                    "order_date"
                ],
            )

        # --------------------------------------------------
        # Orders by date
        # --------------------------------------------------

        if (
            "orders by date" in normalized
            or "order count by date" in normalized
            or "daily orders" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ],
                dimensions=[
                    "order_date"
                ],
            )

        # --------------------------------------------------
        # Total revenue
        # --------------------------------------------------

        if (
            "total revenue" in normalized
            or "total sales" in normalized
            or "how much revenue" in normalized
            or "how much did we make" in normalized
            or "how much did we earn" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "total_revenue"
                ]
            )

        # --------------------------------------------------
        # Order count
        # --------------------------------------------------

        if (
            "order count" in normalized
            or "number of orders" in normalized
            or "how many orders" in normalized
        ):
            return AnalystIntent(
                metrics=[
                    "order_count"
                ]
            )

        raise ValueError(
            f"Unable to interpret analytical question: "
            f"{question}"
        )


def run_tests():
    """
    Verify natural-language questions are converted into
    the expected semantic intents.
    """

    interpreter = IntentInterpreter()

    print(
        "FLOWMART INTENT INTERPRETER"
    )
    print(
        "=========================="
    )

    print("\nTest 1 — Total Revenue")

    intent = interpreter.interpret(
        "How much revenue did we make?"
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == []

    print(
        "[PASS] Total revenue question interpreted."
    )

    print("\nTest 2 — Completed Orders")

    intent = interpreter.interpret(
        "How many completed orders do we have?"
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "order_count"
    ]

    assert intent.filters == {
        "status": "completed"
    }

    print(
        "[PASS] Completed-order question interpreted."
    )

    print("\nTest 3 — Revenue by Date")

    intent = interpreter.interpret(
        "Show me revenue by date."
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == [
        "order_date"
    ]

    print(
        "[PASS] Revenue-by-date question interpreted."
    )

    print("\nTest 4 — Orders by Status")

    intent = interpreter.interpret(
        "Show order count by status."
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "order_count"
    ]

    assert intent.dimensions == [
        "status"
    ]

    print(
        "[PASS] Orders-by-status question interpreted."
    )

    print("\nTest 5 — Average Order Value")

    intent = interpreter.interpret(
        "What is our average order value?"
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "average_order_value"
    ]

    print(
        "[PASS] AOV question interpreted."
    )

    print("\nTest 6 — Unknown Question")

    try:
        interpreter.interpret(
            "Which product is flying through the moon?"
        )

        print(
            "[FAIL] Unknown question was accepted."
        )

        return False

    except ValueError:
        print(
            "[PASS] Unknown question rejected."
        )

    print("\n==========================")
    print(
        "INTENT INTERPRETER PASSED"
    )
    print(
        "=========================="
    )

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )