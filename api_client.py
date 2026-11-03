"""
Thin client for the IFB220 Azure OpenAI portal.

Handles retries with backoff, converts SDK errors into user-safe messages,
and records every call in the usage tracker.
"""

import time

from openai import AzureOpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError

import config
import usage


class ApiClientError(Exception):
    """
    Raised when a call to the API fails after retries. The message is safe to
    show the user. `detail` holds the technical cause (status, error code,
    provider message) for the log only.
    """

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


def _filtered_categories(inner):
    """
    Content filter categories that blocked the request, as 'name' or 'name:severity'.
    Azure reports them under innererror.content_filter_result. Returns [] if absent.
    """
    innererror = inner.get("innererror") if isinstance(inner.get("innererror"), dict) else {}
    result = innererror.get("content_filter_result")
    if not isinstance(result, dict):
        return []
    found = []
    for name, info in sorted(result.items()):
        if isinstance(info, dict) and info.get("filtered"):
            severity = info.get("severity")
            found.append(f"{name}:{severity}" if severity else name)
    return found


def _error_detail(error):
    """
    Summarise an API status error for the log, for example
    'status=400 code=content_filter filtered=self_harm:medium message=...'.
    """
    code = getattr(error, "code", None)
    body = getattr(error, "body", None)
    message = None
    categories = []
    if isinstance(body, dict):
        inner = body.get("error") if isinstance(body.get("error"), dict) else body
        code = code or inner.get("code")
        message = inner.get("message")
        categories = _filtered_categories(inner)
    parts = [f"status={error.status_code}"]
    if code:
        parts.append(f"code={code}")
    if categories:
        parts.append("filtered=" + ",".join(categories))
    if message:
        parts.append(f"message={str(message)[:300]}")
    return " ".join(parts)


_client = None


def _get_client():
    """Create the client on first use so importing this module needs no API key."""
    global _client
    if _client is None:
        if not config.API_KEY:
            raise ApiClientError(
                "API_KEY environment variable is not set. Export it before running."
            )
        _client = AzureOpenAI(
            azure_endpoint=config.AZURE_ENDPOINT,
            api_key=config.API_KEY,
            api_version=config.API_VERSION,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    return _client


def chat_completion(messages, purpose="chat", temperature=0.4, max_tokens=None,
                    retries=2, backoff_seconds=1.5):
    """
    Send a chat completion request to GPT-4.1-mini.

    purpose labels the call in the usage tracker ("chat", "input_judge",
    "output_judge", "summary"). Returns a dict with the reply text, token
    usage, and latency. Raises ApiClientError with a friendly message on failure.
    """
    if max_tokens is None:
        max_tokens = config.RESERVE_TOKENS_FOR_RESPONSE
    attempt = 0
    while True:
        try:
            start = time.monotonic()
            response = _get_client().chat.completions.create(
                model=config.MODEL_CHAT,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = time.monotonic() - start
            text = response.choices[0].message.content or ""
            usage_info = response.usage
            prompt_tokens = usage_info.prompt_tokens if usage_info else None
            completion_tokens = usage_info.completion_tokens if usage_info else None
            usage.tracker.record_chat(purpose, prompt_tokens, completion_tokens, latency)
            return {
                "text": text,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_seconds": round(latency, 3),
            }

        except RateLimitError:
            attempt += 1
            if attempt > retries:
                usage.tracker.record_error()
                raise ApiClientError(
                    "The assistant is receiving too many requests right now. "
                    "Please try again in a moment."
                )
            time.sleep(backoff_seconds * attempt)

        except (APIConnectionError, APITimeoutError):
            attempt += 1
            if attempt > retries:
                usage.tracker.record_error()
                raise ApiClientError(
                    "Could not reach the AI service. Please check your connection "
                    "and try again."
                )
            time.sleep(backoff_seconds * attempt)

        except APIStatusError as error:
            # Bad requests, auth failures, content filter blocks: not retryable.
            usage.tracker.record_error()
            detail = _error_detail(error)
            if "content_filter" in detail:
                message = ("The AI service's content filter blocked that message. "
                           "Please try rephrasing it.")
            else:
                message = (f"The AI service rejected the request (status {error.status_code}). "
                           "Please try rephrasing your message.")
            raise ApiClientError(message, detail=detail) from error


def get_embedding(text, retries=2, backoff_seconds=1.5):
    """
    Get an embedding vector for a piece of text using config.MODEL_EMBEDDING.
    Raises ApiClientError with a friendly message on failure.
    """
    attempt = 0
    while True:
        try:
            start = time.monotonic()
            response = _get_client().embeddings.create(
                model=config.MODEL_EMBEDDING,
                input=text,
            )
            latency = time.monotonic() - start
            tokens = response.usage.total_tokens if getattr(response, "usage", None) else None
            usage.tracker.record_embedding(tokens, latency)
            return response.data[0].embedding

        except RateLimitError:
            attempt += 1
            if attempt > retries:
                usage.tracker.record_error()
                raise ApiClientError("Embedding service is rate-limited. Please try again shortly.")
            time.sleep(backoff_seconds * attempt)

        except (APIConnectionError, APITimeoutError):
            attempt += 1
            if attempt > retries:
                usage.tracker.record_error()
                raise ApiClientError("Could not reach the embedding service.")
            time.sleep(backoff_seconds * attempt)

        except APIStatusError as error:
            usage.tracker.record_error()
            raise ApiClientError(
                f"The embedding service rejected the request (status {error.status_code}).",
                detail=_error_detail(error),
            ) from error

