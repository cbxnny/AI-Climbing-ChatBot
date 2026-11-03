"""
Structured JSON-lines logging for the assistant.

Every turn logs the user input, each guardrail layer's decision, token usage,
and latency. Session start and end events carry cumulative usage. The log is
used for operational monitoring, security auditing, and as testing evidence.
"""

import json
import time
import uuid

import config

MAX_LOGGED_CHARS = 2000


def _write(entry):
    entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    with open(config.LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")


def new_session_id():
    return str(uuid.uuid4())


def log_turn(session_id, user_input, guardrail_results, final_decision,
             response_text=None, prompt_tokens=None, completion_tokens=None,
             latency_seconds=None, error=None, blocked_by=None, error_detail=None):
    """
    Log a single conversation turn.

    guardrail_results: list of dicts like
        {"layer": "keyword_prefilter", "allowed": True, "reason": "..."}
    final_decision: "answered", "refused", "smalltalk", "error", "rejected_length"
    blocked_by: name of the layer that stopped the turn, if any
    """
    _write({
        "event": "turn",
        "session_id": session_id,
        "user_input": user_input[:MAX_LOGGED_CHARS],
        "input_length": len(user_input),
        "guardrail_results": guardrail_results,
        "final_decision": final_decision,
        "blocked_by": blocked_by,
        "response_text": response_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_seconds": latency_seconds,
        "error": error,
        "error_detail": error_detail,
    })


def log_context_event(session_id, event_type, details):
    """Log context management events such as summarising history."""
    _write({
        "event": "context_management",
        "session_id": session_id,
        "type": event_type,
        "details": details,
    })


def log_security_event(session_id, event_type, details):
    """Log events worth a security reviewer's attention (drift, session cutoff, leaks)."""
    _write({
        "event": "security",
        "session_id": session_id,
        "type": event_type,
        "details": details,
    })


def log_session_start(session_id):
    _write({"event": "session_start", "session_id": session_id,
            "model_chat": config.MODEL_CHAT, "model_embedding": config.MODEL_EMBEDDING,
            "topic": config.TOPIC_NAME})


def log_session_end(session_id, turn_count, usage_summary=None):
    _write({"event": "session_end", "session_id": session_id,
            "turn_count": turn_count, "usage": usage_summary})

