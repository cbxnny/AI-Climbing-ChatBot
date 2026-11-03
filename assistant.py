"""
The assistant core: one conversation session that wires guardrails, context
management, the API client, usage tracking, and logging together.

main.py is a thin CLI around this class, and run_adversarial.py drives it
programmatically to produce testing evidence.
"""

import api_client
import config
import context_manager
import guardrails
import audit_log
import usage


class Assistant:
    def __init__(self, reference_embeddings, session_id=None):
        self.session_id = session_id or audit_log.new_session_id()
        self.reference_embeddings = reference_embeddings
        self.context = context_manager.ConversationContext(self.session_id)
        self.drift = guardrails.DriftTracker()
        self.turns = 0
        self.refusals = 0
        self.ended = False
        self.last_topic_message = None  # last user message that was answered
        self.pending_refused = None     # previous message if it was refused, else None
        self._start_tokens = usage.tracker.total_tokens
        audit_log.log_session_start(self.session_id)

    def session_tokens(self):
        return usage.tracker.total_tokens - self._start_tokens

    def close(self):
        audit_log.log_session_end(self.session_id, self.turns, usage.tracker.summary())


    def _result(self, reply, decision, results=None, blocked_by=None):
        return {"reply": reply, "decision": decision,
                "results": results or [], "blocked_by": blocked_by,
                "ended": self.ended}

    @staticmethod
    def _blocked_layer(results):
        # The deciding layer is the last one that said no (a borderline embedding
        # result is followed by the judge or strict mode, which make the call).
        for entry in reversed(results):
            if not entry.get("allowed", True):
                return entry["layer"]
        return None

    def _refuse(self, text, results, count_violation=True):
        """Common refusal path: log, count, and end the session if abused."""
        blocked_by = self._blocked_layer(results)
        self.pending_refused = text  # a short follow-up must not escape via old context
        if count_violation:
            self.refusals += 1
        audit_log.log_turn(self.session_id, text, results, "refused", blocked_by=blocked_by)
        if self.refusals >= config.MAX_REFUSALS_PER_SESSION:
            self.ended = True
            audit_log.log_security_event(self.session_id, "session_ended_too_many_refusals",
                                      {"refusals": self.refusals})
            return self._result(config.SESSION_LIMIT_MESSAGE, "session_limit", results, blocked_by)
        return self._result(config.REFUSAL_MESSAGE, "refused", results, blocked_by)

  

    def handle(self, user_input):
        """Process one user message and return a result dict (see _result)."""
        text = user_input.strip()
        if not text:
            return self._result("", "empty")
        if self.ended:
            return self._result(config.SESSION_LIMIT_MESSAGE, "session_limit")

        self.turns += 1

        if len(text) > config.MAX_INPUT_CHARS:
            audit_log.log_turn(self.session_id, text, [], "rejected_length",
                            blocked_by="length_cap")
            return self._result(config.TOO_LONG_MESSAGE, "rejected_length",
                                blocked_by="length_cap")

        kind = guardrails.smalltalk_kind(text)
        if kind:
            reply = config.GREETING_REPLY if kind == "greeting" else config.FAREWELL_REPLY
            results = [{"layer": "smalltalk", "allowed": True, "reason": kind}]
            audit_log.log_turn(self.session_id, text, results, "smalltalk", response_text=reply)
            return self._result(reply, "smalltalk", results)

        if usage.tracker.over_limit(self._start_tokens):
            self.ended = True
            audit_log.log_security_event(self.session_id, "session_ended_token_limit",
                                      {"session_tokens": self.session_tokens()})
            return self._result(config.SESSION_LIMIT_MESSAGE, "session_limit")

        strict = self.drift.is_drifting()
        # After a refusal, a short follow-up is read against the refused message.
        # Otherwise it is read against the last answered message.
        context_text = self.pending_refused or self.last_topic_message
        allowed, results = guardrails.run_input_guardrails(
            text, self.reference_embeddings,
            context_text=context_text, strict=strict,
            context_refused=bool(self.pending_refused),
        )
        if strict:
            audit_log.log_security_event(self.session_id, "strict_mode_active",
                                      {"history": self.drift.history})
        self.drift.record(allowed)
        if not allowed:
            return self._refuse(text, results)

        # Only messages that passed the guardrails ever enter the context.
        self.context.add_user_message(text)
        try:
            result = api_client.chat_completion(self.context.build_messages())
        except api_client.ApiClientError as error:
            self.context.discard_last_user_message()
            audit_log.log_turn(self.session_id, text, results, "error", error=str(error),
                            blocked_by="api_error", error_detail=error.detail)
            return self._result(str(error), "error", results, "api_error")

        output_ok, output_results = guardrails.output_check(result["text"])
        results.extend(output_results)
        if not output_ok:
            self.context.discard_last_user_message()
            self.drift.history[-1:] = [False]  # the turn did not end up on-topic
            if any(r["layer"] == "prompt_leak_check" and not r["allowed"] for r in output_results):
                audit_log.log_security_event(self.session_id, "prompt_leak_blocked",
                                          {"user_input": text[:200]})
            return self._refuse(text, results)

        self.context.add_assistant_message(result["text"])
        self.last_topic_message = text
        self.pending_refused = None
        audit_log.log_turn(
            self.session_id, text, results, "answered",
            response_text=result["text"],
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            latency_seconds=result["latency_seconds"],
        )
        return self._result(result["text"], "answered", results)

