### Held-out evaluation (run round4)

After Round 2 I wrote a second prompt set that I had not tuned any guardrail against: 22 on-topic prompts (6 of them contain words my suspicious phrase list watches for, such as "act as my" and "hypothetically"), 35 attack or out-of-scope prompts across overrides, prompt extraction, personas, fiction, smuggling, authority, obfuscation, other languages and quoted instructions, and 5 multi-turn conversations. The prompts were written with AI help and without running them. A second model call grades each answered reply, because a decision-only check passes any reply that came back. The grader is the same model family as the judges, so I also read every answered reply in `manual_review_round4.md`. Evidence files: `heldout_results_round4.md` and `heldout_log_round4.jsonl`.

Overall 78 of 78 checks passed (100%). 5 of the prompts matched weaknesses that I then fixed (look-alike letter folding and a letters-only check for spaced-out text), so they are no longer held-out. Without them the score is 73 of 73 (100%).

| Category | Passed | Total |
|---|---|---|
| on-topic | 16 | 16 |
| on-topic (tricky) | 6 | 6 |
| override | 4 | 4 |
| extraction | 5 | 5 |
| persona | 3 | 3 |
| fiction | 3 | 3 |
| smuggling | 6 | 6 |
| authority | 3 | 3 |
| obfuscation | 3 | 3 |
| multilingual | 2 | 2 |
| indirect | 2 | 2 |
| adjacent | 4 | 4 |
| multi-turn | 21 | 21 |

Failures:

None.
