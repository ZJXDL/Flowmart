from pathlib import Path
import json
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from analyst_intent import AnalystIntent
from llm_client import LLMClient


class LLMIntentInterpreter:
    """
    Converts LLM-generated structured JSON into a validated
    Flowmart AnalystIntent.

    The LLM proposes an intent.

    The semantic registry determines whether that intent
    is actually valid.

    Deterministic semantic rules protect important analytical
    meaning from LLM interpretation errors.
    """

    def __init__(
        self,
        llm_client,
        semantic_registry,
    ):
        if not isinstance(llm_client, LLMClient):
            raise TypeError(
                "llm_client must implement LLMClient."
            )

        self.llm_client = llm_client
        self.registry = semantic_registry

    def _build_system_prompt(self):
        """
        Build the semantic context supplied to the LLM.
        """

        metrics = self.registry.list_metrics()
        dimensions = self.registry.list_dimensions()

        metric_text = "\n".join(
            f"- {name}"
            for name in metrics
        )

        dimension_text = "\n".join(
            f"- {name}"
            for name in dimensions
        )

        return f"""
You are the Flowmart AI Analyst intent interpreter.

Your job is to translate a user's analytical question into
a structured JSON intent.

Available metrics:

{metric_text}

Available dimensions:

{dimension_text}

IMPORTANT SEMANTIC RULE:

A business entity mentioned inside a metric name does NOT
automatically become a grouping dimension.

For example:

"revenue per customer"

means the single metric:

revenue_per_customer

with NO dimensions.

It does NOT mean:

revenue_per_customer grouped by customer_id.

Only add customer_id when the user explicitly asks for a
customer-level breakdown, such as:

"revenue per customer by customer"
"show revenue for each customer"
"revenue by customer"

Similarly, do not infer a grouping dimension merely because
a metric name contains words such as customer, order, status,
or date.

Dimensions represent explicit analytical grouping requests.

Important date rules:

- "order_date" means the calendar date on which an order was created.
- "created_at" means the exact order creation timestamp.
- When the user says "by date", "daily", "per day", "each day",
  or asks for a date-level breakdown, use "order_date".
- Do NOT use "created_at" for a calendar-date grouping request.
- Only use "created_at" when the user explicitly asks for timestamps,
  exact creation times, or time-of-day-level analysis.

Examples:

"Revenue per customer"
→ metrics: ["revenue_per_customer"]
→ dimensions: []

"Revenue by customer"
→ metrics: ["total_revenue"]
→ dimensions: ["customer_id"]

"Revenue per customer by customer"
→ metrics: ["revenue_per_customer"]
→ dimensions: ["customer_id"]

"Revenue by date"
→ metrics: ["total_revenue"]
→ dimensions: ["order_date"]

"Daily revenue"
→ metrics: ["total_revenue"]
→ dimensions: ["order_date"]

"Orders by date"
→ metrics: ["order_count"]
→ dimensions: ["order_date"]

Return ONLY a valid JSON object.

The response MUST use exactly this structure:

{{
  "metrics": ["metric_name"],
  "dimensions": ["dimension_name"],
  "filters": {{
    "dimension_name": "value"
  }}
}}

Rules:

1. Only use metrics from the available metric list.
2. Only use dimensions from the available dimension list.
3. Never invent metrics.
4. Never invent dimensions.
5. Filters must reference valid dimensions.
6. Never generate SQL.
7. Never explain your reasoning.
8. Never use Markdown code fences.
9. Never add text before or after the JSON.
10. If the question cannot be answered using the available metrics
    and dimensions, do not invent a metric or dimension.
11. Preserve the user's requested analytical granularity.
12. For calendar-date grouping, always use "order_date".
13. Do not silently convert a grouping request into a non-grouped metric.
14. Do not silently replace an explicitly requested dimension with
    another available dimension.
15. Do not add a dimension merely because a metric name contains
    a word associated with that dimension.
""".strip()

    def _extract_json(self, raw_response):
        """
        Extract a JSON object from an LLM response.
        """

        if not isinstance(raw_response, str):
            raise ValueError(
                "LLM response must be text."
            )

        text = raw_response.strip()

        if not text:
            raise ValueError(
                "LLM returned an empty response."
            )

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if fenced_match:
            fenced_json = fenced_match.group(1)

            try:
                return json.loads(
                    fenced_json
                )
            except json.JSONDecodeError:
                pass

        start = text.find("{")

        if start != -1:
            decoder = json.JSONDecoder()

            try:
                data, _ = decoder.raw_decode(
                    text[start:]
                )

                return data

            except json.JSONDecodeError:
                pass

        raise ValueError(
            "LLM returned invalid JSON."
        )

    def _validate_explicit_dimension_request(
        self,
        question,
    ):
        """
        Validate explicit "by X" dimension requests.
        """

        normalized = question.strip().lower()

        dimension_aliases = {
            "date": "order_date",
            "day": "order_date",
            "status": "status",
            "customer": "customer_id",
            "customer id": "customer_id",
            "customer_id": "customer_id",
            "order": "order_id",
            "order id": "order_id",
            "order_id": "order_id",
            "created at": "created_at",
            "created_at": "created_at",
            "updated at": "updated_at",
            "updated_at": "updated_at",
        }

        matches = re.findall(
            r"\bby\s+([a-zA-Z_][a-zA-Z0-9_ ]*)",
            normalized,
        )

        for raw_dimension in matches:
            dimension_text = raw_dimension.strip()

            dimension_text = re.split(
                r"\b(?:and|then|over|for|where)\b",
                dimension_text,
                maxsplit=1,
            )[0].strip()

            if not dimension_text:
                continue

            dimension_text = dimension_text.rstrip(
                ".,?!:;"
            ).strip()

            if not dimension_text:
                continue

            mapped_dimension = dimension_aliases.get(
                dimension_text
            )

            if mapped_dimension is None:
                available_dimensions = set(
                    self.registry.list_dimensions()
                )

                if dimension_text in available_dimensions:
                    mapped_dimension = dimension_text
                else:
                    raise ValueError(
                        f"Unknown dimension: {dimension_text}"
                    )

        return True

    def _apply_question_semantic_rules(
        self,
        question,
        data,
    ):
        """
        Apply deterministic semantic rules that depend on
        the wording of the user's question.
        """

        normalized = question.strip().lower()

        date_grouping_phrases = (
            "by date",
            "by day",
            "daily",
            "per day",
            "each day",
            "day by day",
        )

        requests_date_grouping = any(
            phrase in normalized
            for phrase in date_grouping_phrases
        )

        if requests_date_grouping:
            dimensions = data.get(
                "dimensions",
                [],
            )

            if not isinstance(dimensions, list):
                raise ValueError(
                    "Intent 'dimensions' must be a list."
                )

            if "order_date" not in dimensions:
                dimensions = [
                    dimension
                    for dimension in dimensions
                    if dimension != "created_at"
                ]

                dimensions.append(
                    "order_date"
                )

            data["dimensions"] = dimensions

        # --------------------------------------------------
        # Revenue per customer is an aggregate KPI.
        #
        # The phrase "customer" inside the metric name must
        # NOT automatically create a customer_id dimension.
        #
        # A customer dimension is retained only when the user
        # explicitly requests a customer-level breakdown.
        # --------------------------------------------------

        revenue_per_customer_requested = (
            "revenue per customer" in normalized
            or "revenue per user" in normalized
        )

        explicit_customer_breakdown = (
            "revenue by customer" in normalized
            or "revenue by user" in normalized
            or "revenue per customer by customer" in normalized
            or "revenue per user by user" in normalized
            or "for each customer" in normalized
            or "for each user" in normalized
        )

        if revenue_per_customer_requested:
            dimensions = data.get(
                "dimensions",
                [],
            )

            if not isinstance(dimensions, list):
                raise ValueError(
                    "Intent 'dimensions' must be a list."
                )

            if not explicit_customer_breakdown:
                dimensions = [
                    dimension
                    for dimension in dimensions
                    if dimension != "customer_id"
                ]

                data["dimensions"] = dimensions

        return data

    def _validate_intent(self, data):
        """
        Validate the LLM's JSON against the semantic registry.
        """

        if not isinstance(data, dict):
            raise ValueError(
                "LLM response must be a JSON object."
            )

        metrics = data.get("metrics")
        dimensions = data.get("dimensions")
        filters = data.get("filters")

        if not isinstance(metrics, list):
            raise ValueError(
                "Intent 'metrics' must be a list."
            )

        if not metrics:
            raise ValueError(
                "Intent must contain at least one metric."
            )

        if not all(
            isinstance(metric, str)
            for metric in metrics
        ):
            raise ValueError(
                "All intent metrics must be strings."
            )

        if not isinstance(dimensions, list):
            raise ValueError(
                "Intent 'dimensions' must be a list."
            )

        if not all(
            isinstance(dimension, str)
            for dimension in dimensions
        ):
            raise ValueError(
                "All intent dimensions must be strings."
            )

        if not isinstance(filters, dict):
            raise ValueError(
                "Intent 'filters' must be an object."
            )

        if not all(
            isinstance(key, str)
            for key in filters.keys()
        ):
            raise ValueError(
                "All filter dimensions must be strings."
            )

        available_metrics = set(
            self.registry.list_metrics()
        )

        available_dimensions = set(
            self.registry.list_dimensions()
        )

        unknown_metrics = (
            set(metrics)
            - available_metrics
        )

        if unknown_metrics:
            raise ValueError(
                "Unknown metric(s): "
                + ", ".join(
                    sorted(unknown_metrics)
                )
            )

        unknown_dimensions = (
            set(dimensions)
            - available_dimensions
        )

        if unknown_dimensions:
            raise ValueError(
                "Unknown dimension(s): "
                + ", ".join(
                    sorted(unknown_dimensions)
                )
            )

        unknown_filters = (
            set(filters.keys())
            - available_dimensions
        )

        if unknown_filters:
            raise ValueError(
                "Unknown filter dimension(s): "
                + ", ".join(
                    sorted(unknown_filters)
                )
            )

        return AnalystIntent(
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
        )

    def interpret(self, question):
        """
        Ask the LLM to interpret a question and validate
        the resulting structured intent.
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        self._validate_explicit_dimension_request(
            question
        )

        system_prompt = (
            self._build_system_prompt()
        )

        raw_response = self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=question,
        )

        data = self._extract_json(
            raw_response
        )

        data = self._apply_question_semantic_rules(
            question,
            data,
        )

        return self._validate_intent(
            data
        )


def run_tests():
    """
    Verify that LLM responses are converted into validated
    semantic intents.
    """

    from llm_client import MockLLMClient
    from semantic.registry import SemanticRegistry

    responses = {
        "How much revenue did we make?":
            '{"metrics":["total_revenue"],'
            '"dimensions":[],"filters":{}}',

        "How many completed orders do we have?":
            '{"metrics":["order_count"],'
            '"dimensions":[],"filters":'
            '{"status":"completed"}}',

        "Show revenue by status.":
            '{"metrics":["total_revenue"],'
            '"dimensions":["status"],'
            '"filters":{}}',

        "Show revenue by date.":
            '{"metrics":["total_revenue"],'
            '"dimensions":["created_at"],'
            '"filters":{}}',

        "Show daily revenue.":
            '{"metrics":["total_revenue"],'
            '"dimensions":[],"filters":{}}',

        "Revenue per customer":
            '{"metrics":["revenue_per_customer"],'
            '"dimensions":["customer_id"],'
            '"filters":{}}',

        "Revenue per customer by customer":
            '{"metrics":["revenue_per_customer"],'
            '"dimensions":["customer_id"],'
            '"filters":{}}',

        "Revenue by customer":
            '{"metrics":["total_revenue"],'
            '"dimensions":["customer_id"],'
            '"filters":{}}',

        "Hallucinated metric":
            '{"metrics":["profit_margin"],'
            '"dimensions":[],"filters":{}}',

        "Hallucinated dimension":
            '{"metrics":["total_revenue"],'
            '"dimensions":["product_name"],'
            '"filters":{}}',

        "Markdown JSON":
            '```json\n'
            '{"metrics":["order_count"],'
            '"dimensions":[],"filters":{}}\n'
            '```',

        "Surrounded JSON":
            'Here is the requested intent:\n'
            '{"metrics":["total_revenue"],'
            '"dimensions":[],"filters":{}}\n'
            'I hope this helps.',

        "Show revenue by unicorn_type":
            '{"metrics":["total_revenue"],'
            '"dimensions":["order_date"],'
            '"filters":{}}',
    }

    client = MockLLMClient(
        responses=responses
    )

    registry = SemanticRegistry()

    interpreter = LLMIntentInterpreter(
        llm_client=client,
        semantic_registry=registry,
    )

    print(
        "FLOWMART LLM INTENT INTERPRETER"
    )
    print(
        "==============================="
    )

    print(
        "\nTest 1 — Revenue"
    )

    intent = interpreter.interpret(
        "How much revenue did we make?"
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == []

    print(
        "[PASS] Revenue intent validated."
    )

    print(
        "\nTest 2 — Completed Orders"
    )

    intent = interpreter.interpret(
        "How many completed orders do we have?"
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "order_count"
    ]

    assert intent.filters == {
        "status": "completed"
    }

    print(
        "[PASS] Completed-order intent validated."
    )

    print(
        "\nTest 3 — Revenue by Status"
    )

    intent = interpreter.interpret(
        "Show revenue by status."
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == [
        "status"
    ]

    print(
        "[PASS] Revenue-by-status intent validated."
    )

    print(
        "\nTest 4 — Revenue by Date"
    )

    intent = interpreter.interpret(
        "Show revenue by date."
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == [
        "order_date"
    ]

    print(
        "[PASS] Revenue-by-date semantic correction applied."
    )

    print(
        "\nTest 5 — Daily Revenue"
    )

    intent = interpreter.interpret(
        "Show daily revenue."
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == [
        "order_date"
    ]

    print(
        "[PASS] Daily-revenue semantic correction applied."
    )

    print(
        "\nTest 6 — Revenue per Customer"
    )

    intent = interpreter.interpret(
        "Revenue per customer"
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "revenue_per_customer"
    ]

    assert intent.dimensions == []

    print(
        "[PASS] Revenue-per-customer "
        "dimension hallucination corrected."
    )

    print(
        "\nTest 7 — Revenue per Customer by Customer"
    )

    intent = interpreter.interpret(
        "Revenue per customer by customer"
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "revenue_per_customer"
    ]

    assert intent.dimensions == [
        "customer_id"
    ]

    print(
        "[PASS] Explicit customer breakdown preserved."
    )

    print(
        "\nTest 8 — Revenue by Customer"
    )

    intent = interpreter.interpret(
        "Revenue by customer"
    )

    print(
        intent.to_dict()
    )

    assert intent.metrics == [
        "total_revenue"
    ]

    assert intent.dimensions == [
        "customer_id"
    ]

    print(
        "[PASS] Revenue-by-customer breakdown preserved."
    )

    print(
        "\nTest 9 — Markdown JSON"
    )

    intent = interpreter.interpret(
        "Markdown JSON"
    )

    assert intent.metrics == [
        "order_count"
    ]

    print(
        "[PASS] Markdown-wrapped JSON parsed."
    )

    print(
        "\nTest 10 — Surrounded JSON"
    )

    intent = interpreter.interpret(
        "Surrounded JSON"
    )

    assert intent.metrics == [
        "total_revenue"
    ]

    print(
        "[PASS] Surrounding text tolerated."
    )

    print(
        "\nTest 11 — Hallucinated Metric"
    )

    try:
        interpreter.interpret(
            "Hallucinated metric"
        )

        print(
            "[FAIL] Hallucinated metric accepted."
        )

        return False

    except ValueError as error:
        print(
            f"[PASS] Hallucinated metric rejected: "
            f"{error}"
        )

    print(
        "\nTest 12 — Hallucinated Dimension"
    )

    try:
        interpreter.interpret(
            "Hallucinated dimension"
        )

        print(
            "[FAIL] Hallucinated dimension accepted."
        )

        return False

    except ValueError as error:
        print(
            f"[PASS] Hallucinated dimension rejected: "
            f"{error}"
        )

    print(
        "\nTest 13 — Unknown Explicit Dimension"
    )

    try:
        interpreter.interpret(
            "Show revenue by unicorn_type"
        )

        print(
            "[FAIL] Unknown explicit dimension accepted."
        )

        return False

    except ValueError as error:
        print(
            f"[PASS] Unknown explicit dimension rejected: "
            f"{error}"
        )

        assert str(error) == (
            "Unknown dimension: unicorn_type"
        )

    print(
        "\n==============================="
    )
    print(
        "LLM INTENT INTERPRETER PASSED"
    )
    print(
        "==============================="
    )

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )