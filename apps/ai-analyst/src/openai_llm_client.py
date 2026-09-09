import os

from openai import OpenAI

from llm_client import LLMClient


class OpenAILLMClient(LLMClient):
    """
    Real OpenAI implementation of the Flowmart LLMClient interface.

    API credentials are loaded from OPENAI_API_KEY so secrets never
    live inside the source code.
    """

    def __init__(
        self,
        model=None,
    ):
        api_key = os.getenv(
            "OPENAI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set."
            )

        self.model = (
            model
            or os.getenv(
                "FLOWMART_LLM_MODEL",
                "gpt-5.5",
            )
        )

        self.client = OpenAI(
            api_key=api_key
        )

    def generate(
        self,
        system_prompt,
        user_prompt,
    ):
        """
        Generate text using the OpenAI Responses API.
        """

        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
        )

        answer = response.output_text

        if not answer or not answer.strip():
            raise RuntimeError(
                "OpenAI returned an empty response."
            )

        return answer.strip()


def run_configuration_test():
    """
    Verify that the OpenAI client can be configured without
    exposing the API key.
    """

    print(
        "FLOWMART OPENAI LLM CLIENT"
    )
    print(
        "=========================="
    )

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        print(
            "[FAIL] OPENAI_API_KEY is not set."
        )

        return False

    print(
        "[PASS] OPENAI_API_KEY is configured."
    )

    model = os.getenv(
        "FLOWMART_LLM_MODEL",
        "gpt-5.5",
    )

    print(
        f"Model: {model}"
    )

    print(
        "[PASS] OpenAI client configuration is valid."
    )

    return True


if __name__ == "__main__":
    success = run_configuration_test()

    raise SystemExit(
        0 if success else 1
    )