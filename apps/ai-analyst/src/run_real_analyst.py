from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from llm_analyst_engine import LLMAnalystEngine
from groq_llm_client import GroqLLMClient


def main():
    print("FLOWMART REAL AI ANALYST")
    print("========================")
    print("Provider: Groq")
    print("Model: openai/gpt-oss-120b")

    llm = GroqLLMClient()

    engine = LLMAnalystEngine(
        llm_client=llm,
        answer_llm_client=llm,
    )

    while True:
        question = input("\nAsk Flowmart > ").strip()

        if not question:
            continue

        if question.lower() in {
            "exit",
            "quit",
            "q",
        }:
            break

        try:
            response = engine.ask(question)

            print("\nIntent:")
            print(response["intent"])

            print("\nSQL:")
            print(response["sql"])

            print("\nResult:")
            print(response["rows"])

            print("\nAnswer:")
            print(response["answer"])

        except Exception as error:
            print(f"\nERROR: {error}")


if __name__ == "__main__":
    main()