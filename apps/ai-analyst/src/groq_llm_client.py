import os

from groq import Groq

from llm_client import LLMClient


class GroqLLMClient(LLMClient):
    """
    Groq implementation of Flowmart's LLMClient interface.

    Uses Groq's native Python SDK rather than the OpenAI
    compatibility client.

    Flowmart uses GPT-OSS for:

        1. Natural-language intent interpretation.
        2. Natural-language analytical answer generation.

    Reasoning is intentionally configured to LOW because
    Flowmart's tasks are constrained semantic and analytical
    operations rather than open-ended reasoning problems.
    """

    DEFAULT_MODEL = "openai/gpt-oss-120b"

    def __init__(self, model=None):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set."
            )

        self.model = (
            model
            or os.getenv(
                "FLOWMART_LLM_MODEL",
                self.DEFAULT_MODEL,
            )
        )

        self.client = Groq(
            api_key=api_key
        )

    def generate(self, system_prompt, user_prompt):
        """
        Generate a response using Groq's native SDK.

        Low reasoning effort is used deliberately because
        Flowmart provides the semantic constraints and performs
        deterministic validation after the LLM responds.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            reasoning_effort="low",
            max_completion_tokens=1000,
        )

        message = response.choices[0].message

        answer = message.content

        if not answer or not answer.strip():
            raise RuntimeError(
                "Groq returned an empty response."
            )

        return answer.strip()


def run_configuration_test():
    """
    Verify that the Groq provider is configured correctly.
    """

    print(
        "FLOWMART GROQ LLM CLIENT"
    )
    print(
        "========================"
    )

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print(
            "[FAIL] GROQ_API_KEY is not set."
        )
        return False

    print(
        "[PASS] GROQ_API_KEY is configured."
    )

    model = os.getenv(
        "FLOWMART_LLM_MODEL",
        GroqLLMClient.DEFAULT_MODEL,
    )

    print(
        f"Model: {model}"
    )

    print(
        "SDK: native Groq Python SDK"
    )

    print(
        "Reasoning effort: low"
    )

    print(
        "Max completion tokens: 1000"
    )

    print(
        "[PASS] Groq client configuration is valid."
    )

    return True


if __name__ == "__main__":
    success = run_configuration_test()

    raise SystemExit(
        0 if success else 1
    )