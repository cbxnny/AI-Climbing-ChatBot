# Content filter diagnosis

Run on 2026-10-23 22:59 against gpt-4.1-mini. Each row is one request.

| Question | Variant | Outcome | Detail |
|---|---|---|---|
| hangboard | full system prompt | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| hangboard | system prompt without the marker line | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| hangboard | minimal system prompt | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| hangboard | no system prompt | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| hangboard | reworded: different wording | ok |  |
| hangboard | reworded: keeps the word hang | ok |  |
| hangboard | reworded: no hang word | ok |  |
| figure eight | full system prompt | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| figure eight | system prompt without the marker line | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| figure eight | minimal system prompt | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| figure eight | no system prompt | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| figure eight | reworded: adds the word knot | BLOCKED | status=400 code=content_filter filtered=self_harm:medium message=The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766 |
| figure eight | reworded: longer wording | ok |  |
| figure eight | reworded: different knot | ok |  |

## How to read this

9 of 14 requests were blocked.

- If a question is blocked with every system prompt variant, including none, the wording of the question triggers the filter and the system prompt is not involved.
- If it is blocked only with the full system prompt, the system prompt wording (for example the rules about revealing instructions) is involved.
- If only some reworded versions pass, the filter is reacting to specific words.
- The `filtered=` part of the detail names the filter category, when the provider reports it.
