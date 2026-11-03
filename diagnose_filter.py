"""
Find out what triggers the provider's content filter on ordinary climbing questions.

Two on-topic questions ("warm up my fingers before hangboarding" and "tie a figure
eight follow-through") are rejected by the Azure content filter with status 400 on
every run, even though they pass every guardrail in this project. This script sends
each question several ways and records which ones get through, so the cause can be
stated from evidence instead of guessed.
"""

import argparse
import re
import sys
import time

import api_client
import config
import eval_files

QUESTIONS = {
    "hangboard": "How should I warm up my fingers before hangboarding?",
    "figure eight": "How do I tie a figure eight follow-through?",
}

REWORDS = {
    "hangboard": [
        ("different wording", "How should I warm up my fingers before a finger board session?"),
        ("keeps the word hang", "What is a good finger warm up before training on a hang board?"),
        ("no hang word", "How should I warm up my fingers before finger strength training?"),
    ],
    "figure eight": [
        ("adds the word knot", "How do I tie a figure eight follow-through knot?"),
        ("longer wording", "What are the steps for the figure eight follow-through knot used to tie in to a harness?"),
        ("different knot", "How do I tie a figure eight knot?"),
    ],
}


def system_variants():
    without_marker = "\n".join(line for line in config.SYSTEM_PROMPT.splitlines()
                               if config.SYSTEM_CANARY not in line)
    minimal = f"You are {config.ASSISTANT_ROLE}. You only discuss {config.TOPIC_NAME}."
    return [
        ("full system prompt", config.SYSTEM_PROMPT),
        ("system prompt without the marker line", without_marker),
        ("minimal system prompt", minimal),
        ("no system prompt", None),
    ]


def attempt(call, system, prompt):
    """Send one request. Returns (outcome, detail)."""
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    try:
        call(messages, purpose="diagnosis", temperature=0, max_tokens=60)
    except api_client.ApiClientError as error:
        return "BLOCKED", error.detail or str(error)
    return "ok", ""


def run(call=None):
    """Run every variant. Returns a list of (question, variant, outcome, detail)."""
    call = call or api_client.chat_completion
    rows = []
    for key, prompt in QUESTIONS.items():
        for name, system in system_variants():
            outcome, detail = attempt(call, system, prompt)
            rows.append((key, name, outcome, detail))
            print(f"[{outcome:7}] {key:13} {name}")
        for name, reworded in REWORDS[key]:
            outcome, detail = attempt(call, config.SYSTEM_PROMPT, reworded)
            rows.append((key, f"reworded: {name}", outcome, detail))
            print(f"[{outcome:7}] {key:13} reworded: {name}")
    return rows


def interpret(rows):
    """
    Plain statements about what the results show, chosen by fixed rules so the
    wording always matches the data. Returns a list of sentences.
    """
    sentences = []
    for key in QUESTIONS:
        mine = [r for r in rows if r[0] == key]
        systems = [r for r in mine if not r[1].startswith("reworded")]
        rewords = [r for r in mine if r[1].startswith("reworded")]
        blocked_systems = [r for r in systems if r[2] == "BLOCKED"]
        if not any(r[2] == "BLOCKED" for r in mine):
            sentences.append(f"The {key} question was not blocked in any variant in this run, "
                             "so the earlier errors did not reproduce.")
            continue
        if len(blocked_systems) == len(systems):
            sentences.append(f"The {key} question was blocked with every system prompt variant, "
                             "including none, so its own wording triggers the filter and the "
                             "system prompt is not involved.")
        elif blocked_systems:
            names = ", ".join(r[1] for r in blocked_systems)
            sentences.append(f"The {key} question was blocked only with: {names}. "
                             "The system prompt wording is involved.")
        else:
            sentences.append(f"The {key} question passed with every system prompt variant in this run.")
        passed = [r[1].replace("reworded: ", "") for r in rewords if r[2] != "BLOCKED"]
        if rewords:
            sentences.append(f"{len(passed)} of {len(rewords)} reworded versions of the {key} question passed"
                             + (f" ({', '.join(passed)})." if passed else "."))
    categories = sorted({m for r in rows if r[2] == "BLOCKED"
                         for m in re.findall(r"filtered=(\S+)", r[3])})
    if categories:
        sentences.append("The provider named these filter categories: " + ", ".join(categories) + ".")
    return sentences


def write_report(rows, tag=""):
    path = eval_files.tagged("filter_diagnosis.md", tag)
    lines = [
        "# Content filter diagnosis", "",
        f"Run on {time.strftime('%Y-%m-%d %H:%M')} against {config.MODEL_CHAT}. Each row is one request.", "",
        "| Question | Variant | Outcome | Detail |", "|---|---|---|---|",
    ]
    for key, name, outcome, detail in rows:
        lines.append(f"| {key} | {name} | {outcome} | {detail.replace('|', '/')} |")
    blocked = [r for r in rows if r[2] == "BLOCKED"]
    lines += ["", "## How to read this", "",
              f"{len(blocked)} of {len(rows)} requests were blocked.", "",
              "- If a question is blocked with every system prompt variant, including none, the "
              "wording of the question triggers the filter and the system prompt is not involved.",
              "- If it is blocked only with the full system prompt, the system prompt wording "
              "(for example the rules about revealing instructions) is involved.",
              "- If only some reworded versions pass, the filter is reacting to specific words.",
              "- The `filtered=` part of the detail names the filter category, when the provider reports it."]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    snippet = [
        "### Content filter investigation", "",
        "Two on-topic questions returned status 400 (`content_filter`) on every run although they "
        "passed every guardrail. `diagnose_filter.py` sends each question with the full system prompt, "
        "the prompt without its internal marker line, a minimal system prompt and no system prompt, "
        "and then sends reworded versions. "
        f"{len(blocked)} of {len(rows)} requests were blocked. " + " ".join(interpret(rows)), "",
        "The assistant does not retry or rephrase a message that the provider's filter blocked, "
        "because that would weaken a safety layer it does not control. It tells the user the filter "
        "blocked the message, and the cause is recorded in the log. Evidence file: `" + path + "`.", ""]
    with open(eval_files.tagged("readme_filter.md", tag), "w", encoding="utf-8") as handle:
        handle.write("\n".join(snippet))
    return blocked


def main():
    parser = argparse.ArgumentParser(description="Find what triggers the provider's content filter.")
    eval_files.add_output_arguments(parser)
    args = parser.parse_args()
    eval_files.console_safe()
    if not config.API_KEY:
        print("API_KEY environment variable is not set.")
        sys.exit(1)
    names = [eval_files.tagged(name, args.tag) for name in ("filter_diagnosis.md", "readme_filter.md")]
    eval_files.prepare_outputs(names, args.overwrite)  # before any API call
    rows = run()
    blocked = write_report(rows, args.tag)
    print(f"\n{len(blocked)} of {len(rows)} requests blocked. Wrote {', '.join(names)}")


if __name__ == "__main__":
    main()
