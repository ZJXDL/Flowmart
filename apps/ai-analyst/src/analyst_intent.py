from dataclasses import dataclass, field


@dataclass
class AnalystIntent:
    """
    Structured representation of what the user wants
    the Flowmart AI Analyst to calculate.

    This object sits between natural-language understanding
    and deterministic analytical execution.
    """

    metrics: list[str]
    dimensions: list[str] = field(default_factory=list)
    filters: dict = field(default_factory=dict)

    def to_dict(self):
        """
        Return the intent as a plain dictionary.
        """

        return {
            "metrics": self.metrics,
            "dimensions": self.dimensions,
            "filters": self.filters,
        }


def run_tests():
    """
    Verify that analyst intents can be created and
    serialized correctly.
    """

    print("FLOWMART ANALYST INTENT")
    print("=======================")

    print("\nTest 1 — Total Revenue")

    intent = AnalystIntent(
        metrics=[
            "total_revenue"
        ]
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == []

    assert intent.filters == {}

    print("[PASS] Basic metric intent created.")

    print("\nTest 2 — Revenue by Date")

    intent = AnalystIntent(
        metrics=[
            "total_revenue"
        ],
        dimensions=[
            "order_date"
        ],
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == [
        "order_date"
    ]

    print("[PASS] Metric + dimension intent created.")

    print("\nTest 3 — Completed Orders")

    intent = AnalystIntent(
        metrics=[
            "order_count"
        ],
        filters={
            "status": "completed"
        },
    )

    print(intent.to_dict())

    assert intent.metrics == [
        "order_count"
    ]

    assert intent.filters == {
        "status": "completed"
    }

    print("[PASS] Filtered intent created.")

    print("\nTest 4 — Revenue by Status")

    intent = AnalystIntent(
        metrics=[
            "total_revenue",
            "order_count",
        ],
        dimensions=[
            "status"
        ],
    )

    print(intent.to_dict())

    assert len(intent.metrics) == 2

    assert intent.dimensions == [
        "status"
    ]

    print("[PASS] Multi-metric intent created.")

    print("\n=======================")
    print("ANALYST INTENT PASSED")
    print("=======================")

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )