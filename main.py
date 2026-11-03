"""
CLI entry point for the topic-restricted assistant.

Commands during a chat: /usage shows token usage, exit or quit ends the session.
"""

import sys

import api_client
import assistant
import config
import guardrails
import usage


def run():
    if not config.API_KEY:
        print("API_KEY environment variable is not set. Export it and try again.")
        sys.exit(1)

    print("=" * 60)
    print(f" {config.TOPIC_NAME.title()} Assistant")
    print(" Type 'exit' or 'quit' to end. Type '/usage' for token usage.")
    print("=" * 60 + "\n")

    print("Preparing topic classifier...")
    try:
        reference_embeddings = guardrails.build_reference_embeddings()
    except api_client.ApiClientError as error:
        # Fail closed: without the classifier the guardrails are incomplete.
        print(f"Could not start the assistant: {error}")
        sys.exit(1)

    session = assistant.Assistant(reference_embeddings)

    while not session.ended:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        if user_input.lower() == "/usage":
            print("\n" + usage.tracker.format() + "\n")
            continue
        if not user_input:
            continue

        result = session.handle(user_input)
        print(f"\nAssistant: {result['reply']}\n")

    session.close()
    print(usage.tracker.format())


if __name__ == "__main__":
    run()

