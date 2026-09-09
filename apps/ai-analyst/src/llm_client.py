from abc import ABC, abstractmethod


class LLMClient(ABC):
    """
    Abstract interface for an LLM provider.

    The AI Analyst depends on this interface rather than on
    a specific provider. This keeps the agent architecture
    provider-independent.
    """

    @abstractmethod
    def generate(self, system_prompt, user_prompt):
        """
        Generate a response from the language model.
        """

        raise NotImplementedError


class MockLLMClient(LLMClient):
    """
    Deterministic mock LLM used during development.

    This allows us to build and test the LLM integration
    without requiring an API key or network access.
    """

    def __init__(self, responses=None):
        self.responses = responses or {}

    def generate(self, system_prompt, user_prompt):
        """
        Return a predefined response for a user question.
        """

        question = user_prompt.strip()

        if question in self.responses:
            return self.responses[question]

        raise ValueError(
            f"No mock response configured for: {question}"
        )


def run_tests():
    """
    Verify the provider abstraction and mock client.
    """

    print(
        "FLOWMART LLM CLIENT"
    )
    print(
        "==================="
    )

    responses = {
        "How much revenue did we make?":
            '{"metrics":["total_revenue"],'
            '"dimensions":[],"filters":{}}',

        "How many completed orders do we have?":
            '{"metrics":["order_count"],'
            '"dimensions":[],"filters":'
            '{"status":"completed"}}',
    }

    client = MockLLMClient(
        responses=responses
    )

    print(
        "\nTest 1 — Revenue question"
    )

    response = client.generate(
        system_prompt="You are the Flowmart AI Analyst.",
        user_prompt="How much revenue did we make?",
    )

    print(
        "Response:"
    )
    print(
        response
    )

    assert "total_revenue" in response

    print(
        "[PASS] Mock LLM generated response."
    )

    print(
        "\nTest 2 — Completed orders"
    )

    response = client.generate(
        system_prompt="You are the Flowmart AI Analyst.",
        user_prompt="How many completed orders do we have?",
    )

    print(
        "Response:"
    )
    print(
        response
    )

    assert "order_count" in response
    assert "completed" in response

    print(
        "[PASS] Mock LLM generated filtered response."
    )

    print(
        "\nTest 3 — Unknown question"
    )

    try:
        client.generate(
            system_prompt="You are the Flowmart AI Analyst.",
            user_prompt="What is happening?",
        )

        print(
            "[FAIL] Unknown question was accepted."
        )

        return False

    except ValueError:
        print(
            "[PASS] Unknown question rejected."
        )

    print(
        "\n==================="
    )
    print(
        "LLM CLIENT PASSED"
    )
    print(
        "==================="
    )

    return True


if __name__ == "__main__":
    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )