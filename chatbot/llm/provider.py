"""Bounded calls and safe diagnostics for the active chatbot provider."""
import logging
from threading import Lock
from time import monotonic

import httpx
from core.settings import settings

logger = logging.getLogger(__name__)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

client = None
if settings.LLM_ENABLED and OpenAI:
    client = OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        timeout=httpx.Timeout(settings.LLM_TIMEOUT, connect=2, pool=2, write=5),
        max_retries=0,
    )

_state_lock = Lock()
_generation_lock = Lock()
_reason = 'not_checked'
_retry_at = 0.0
_checked_at = 0.0
_ready = False
COOLDOWN = 30


def _update(ready, reason):
    global _ready, _reason, _checked_at, _retry_at
    with _state_lock:
        _ready, _reason, _checked_at = ready, reason, monotonic()
        _retry_at = 0 if ready else monotonic() + COOLDOWN


def failure_reason(exc):
    code = getattr(exc, 'status_code', None)
    if code in (401, 403):
        return 'authentication_failed'
    if code == 404:
        return 'model_missing'
    if code == 429:
        return 'rate_limited'
    if isinstance(exc, httpx.TimeoutException) or 'Timeout' in type(exc).__name__:
        return 'timeout'
    if isinstance(exc, httpx.ConnectError) or 'Connection' in type(exc).__name__:
        return 'offline'
    return 'provider_error'


def status(probe=False):
    """Never expose keys, provider exception bodies or student data."""
    if not settings.LLM_ENABLED:
        return {'ready': False, 'model': settings.LLM_MODEL, 'reason': 'disabled'}
    if client is None:
        return {'ready': False, 'model': settings.LLM_MODEL, 'reason': 'sdk_missing'}
    with _state_lock:
        should_probe = probe and monotonic() - _checked_at >= 5
    if should_probe:
        try:
            with httpx.Client(timeout=2) as http:
                response = http.get(settings.LLM_BASE_URL.rstrip('/') + '/models',
                    headers={'Authorization': 'Bearer ' + settings.LLM_API_KEY})
                if response.status_code in (401, 403):
                    _update(False, 'authentication_failed')
                else:
                    response.raise_for_status()
                    models = {row['id'] for row in response.json().get('data', [])}
                    _update(settings.LLM_MODEL in models,
                            'ready' if settings.LLM_MODEL in models else 'model_missing')
        except Exception as exc:
            _update(False, failure_reason(exc))
    with _state_lock:
        return {'ready': _ready, 'model': settings.LLM_MODEL, 'reason': _reason}


def generate(messages, selected_client=None):
    """A failed provider gets a cooldown; concurrent requests use fallback replies."""
    selected_client = selected_client or client
    if not settings.LLM_ENABLED or selected_client is None:
        return None, False
    with _state_lock:
        if monotonic() < _retry_at:
            return None, False
    if not _generation_lock.acquire(blocking=False):
        return None, False
    try:
        options = {}
        if settings.LLM_REASONING_EFFORT:
            options['reasoning_effort'] = settings.LLM_REASONING_EFFORT
        response = selected_client.chat.completions.create(
            model=settings.LLM_MODEL, messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS, stream=False,
            **options,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            _update(False, 'empty_response')
            return None, False
        _update(True, 'ready')
        return content.strip(), True
    except Exception as exc:
        reason = failure_reason(exc)
        _update(False, reason)
        logger.warning('Chat model unavailable: %s (%s)', reason, type(exc).__name__)
        return None, False
    finally:
        _generation_lock.release()
