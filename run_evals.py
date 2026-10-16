"""
Evaluation set for the agent — checks BEHAVIOUR, not exact wording.

Each case runs several times, because the model is not deterministic.
Rerun after every change to prompts.py or tool_schemas.py.

Run:  python run_evals.py            (3 runs per case)
      python run_evals.py --runs 1   (quick check)

Costs a few gpt-4o-mini calls per case per run.
"""
import argparse

from agent.loop import run_agent
from agent.prompts import SYSTEM_PROMPT

CASES = [
    {
        "question": "Where is my headphones order?",
        "must_call": ["identify_order", "get_order", "track_package", "get_delivery_estimate"],
    },
    {
        "question": "My office chair has not arrived yet",
        "must_call": ["track_package", "get_delivery_estimate"],
        "answer_mentions_any": ["leipzig", "bulky", "sorting"],     # the note must reach the user
    },
    {
        "question": "My Nintendo Switch says delivered but I can't find it",
        "must_call": ["track_package"],
        "answer_mentions_any": ["front door"],
    },
    {
        "question": "Where is my Monday order?",
        "must_not_call": ["get_order"],                              # 2 matches: ask, don't pick
        "answer_mentions_any": ["?"],
    },
    {
        "question": "What's the status of ORDER-004?",
        "must_call": ["get_order"],
        "must_not_call": ["identify_order"],                         # ID given: go straight to get_order
    },
    {
        "question": "When does my Echo Dot arrive?",
        "answer_mentions_any": ["today", "this afternoon"],         # out for delivery, confidence high
    },
    {
        "question": "When will my running shoes arrive?",
        "answer_mentions_any": ["october 6", "6 october", "2026-10-06", "oct 6"],   # carrier reschedule
    },
    {
        "question": "What happened to my air fryer?",
        "answer_mentions_any": ["redeliver", "7 days", "october 7", "returned"],   # action + deadline
    },
    {
        "question": "Where is my Logitech mouse?",
        "answer_mentions_any": ["cancel"],                           # cancelled order, no tracking
    },
]


def tools_called(history: list) -> list[str]:
    """Names of all tools the model requested, read from the history."""
    names = []
    for entry in history:
        for tool_call in entry.get("tool_calls", []):
            names.append(tool_call["function"]["name"])
    return names


def check(case: dict, answer: str, called: list[str]) -> list[str]:
    """Returns a list of failure messages — empty means the run passed."""
    failures = []
    for name in case.get("must_call", []):
        if name not in called:
            failures.append(f"did not call {name}")
    for name in case.get("must_not_call", []):
        if name in called:
            failures.append(f"called {name}")
    expected = case.get("answer_mentions_any")
    if expected and not any(word in answer.lower() for word in expected):
        failures.append(f"answer mentions none of {expected}")
    return failures


def main(runs: int) -> None:
    total_passed = 0
    for case in CASES:
        passed = 0
        problems = []
        for _ in range(runs):
            history = [{"role": "system", "content": SYSTEM_PROMPT}]
            answer, history = run_agent(case["question"], history)
            failures = check(case, answer, tools_called(history))
            if failures:
                problems.append((failures, tools_called(history), answer))
            else:
                passed += 1

        mark = "PASS" if passed == runs else "FAIL"
        print(f"[{mark}] {passed}/{runs}  {case['question']}")
        for failures, called, answer in problems[:1]:              # show the first failing run
            print(f"         why:     {'; '.join(failures)}")
            print(f"         tools:   {' -> '.join(called) or '(none)'}")
            print(f"         answer:  {answer[:160]}")
        total_passed += passed

    total = len(CASES) * runs
    print(f"\n{total_passed}/{total} runs passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    main(parser.parse_args().runs)
