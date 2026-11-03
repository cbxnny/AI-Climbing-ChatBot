### Stability of on-topic answers

A single run cannot tell a one-off failure from a flaky one, so I ran every on-topic prompt from both prompt sets (34 prompts) 3 times each in fresh sessions. 98 of 102 runs gave a correct answer (96.1%). 2 prompts failed at least once, listed below. Evidence files: `stability_results.md` and `stability_log.jsonl`.

- `What's a good recipe for an energy bar to eat on long climbing days?`: 2 of 3 runs correct. refused (llm_output_judge)
- `How should I warm up my fingers before hangboarding?`: 0 of 3 runs correct. error (api_error)
