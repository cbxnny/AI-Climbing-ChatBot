"""
Service usage tracking.

A single process-wide tracker records every API call (chat, embeddings,
classifier judges, summaries) with token counts and latency, so usage can
be reported to the user, written to the log, and capped per session.
"""

import config


class UsageTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = {}              
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.embedding_tokens = 0
        self.total_latency = 0.0
        self.errors = 0

    def record_chat(self, purpose, prompt_tokens, completion_tokens, latency):
        self.calls[purpose] = self.calls.get(purpose, 0) + 1
        self.prompt_tokens += prompt_tokens or 0
        self.completion_tokens += completion_tokens or 0
        self.total_latency += latency or 0.0

    def record_embedding(self, tokens, latency):
        self.calls["embedding"] = self.calls.get("embedding", 0) + 1
        self.embedding_tokens += tokens or 0
        self.total_latency += latency or 0.0

    def record_error(self):
        self.errors += 1

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens + self.embedding_tokens

    def over_limit(self, since_tokens=0):
        """True once tokens used since `since_tokens` reach the session limit."""
        return (self.total_tokens - since_tokens) >= config.SESSION_TOKEN_LIMIT

    def summary(self):
        return {
            "calls": dict(self.calls),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "embedding_tokens": self.embedding_tokens,
            "total_tokens": self.total_tokens,
            "total_latency_seconds": round(self.total_latency, 2),
            "errors": self.errors,
        }

    def format(self):
        data = self.summary()
        calls = ", ".join(f"{name}={count}" for name, count in sorted(data["calls"].items())) or "none"
        return (
            f"API calls: {calls}\n"
            f"Tokens: prompt={data['prompt_tokens']} completion={data['completion_tokens']} "
            f"embedding={data['embedding_tokens']} total={data['total_tokens']} "
            f"(session limit {config.SESSION_TOKEN_LIMIT})\n"
            f"Time spent in API calls: {data['total_latency_seconds']}s, errors: {data['errors']}"
        )


tracker = UsageTracker()

