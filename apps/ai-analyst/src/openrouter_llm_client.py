import os

from openai import OpenAI

from llm_client import LLMClient


class OpenRouterLLMClient(LLMClient):
    """
    OpenRouter implementation of Flowmart's LLMClient interface.

    Uses OpenRouter's OpenAI-compatible API so Flowmart can switch
    between providers without changing the AI Analyst architecture.
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, model=None):
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is not set."
            )

        self.model = (
            model
            or os.getenv(
                "FLOWMART_LLM_MODEL",
                "openrouter/free",
            )
        )

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
        )

    def generate(self, system_prompt, user_prompt):
        """
        Generate text through OpenRouter's OpenAI-compatible API.
        """

        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
        )

        answer = response.output_text

        if not answer or not answer.strip():
            raise RuntimeError(
                "OpenRouter returned an empty response."
            )

        return answer.strip()


def run_configuration_test():
    """
    Verify that the OpenRouter provider can be configured
    without exposing the API key.
    """

    print("FLOWMART OPENROUTER LLM CLIENT")
    print("==============================")

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        print("[FAIL] OPENROUTER_API_KEY is not set.")
        return False

    print("[PASS] OPENROUTER_API_KEY is configured.")

    model = os.getenv(
        "FLOWMART_LLM_MODEL",
        "openrouter/free",
    )

    print(f"Model: {model}")
    print("[PASS] OpenRouter client configuration is valid.")

    return True


if __name__ == "__main__":
    success = run_configuration_test()

    raise SystemExit(
        0 if success else 1
    )