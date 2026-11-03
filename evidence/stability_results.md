# Stability results

Run on 2026-10-23 22:50. 34 on-topic prompts, 3 runs each, each run in a fresh session.

**98/102 runs gave a correct answer (96.1%).**

Usage: {"calls": {"embedding": 96, "chat": 93, "output_judge": 93, "grader": 92, "input_judge": 15}, "prompt_tokens": 136291, "completion_tokens": 29426, "embedding_tokens": 1245, "total_tokens": 166962, "total_latency_seconds": 493.26, "errors": 3} in 506s.

## Prompts that failed at least once

| Prompt | Correct runs | Failure details |
|---|---|---|
| `How should I warm up my fingers before hangboarding?` | 0/3 | error (api_error) |
| `What's a good recipe for an energy bar to eat on long climbing days?` | 2/3 | refused (llm_output_judge) |
