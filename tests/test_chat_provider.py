from types import SimpleNamespace
import httpx
import pytest
from chatbot.llm import provider
from core.settings import Settings


@pytest.fixture(autouse=True)
def reset_provider(monkeypatch):
    monkeypatch.setattr(provider.settings, 'LLM_ENABLED', True)
    monkeypatch.setattr(provider, '_retry_at', 0)
    monkeypatch.setattr(provider, '_checked_at', 0)
    monkeypatch.setattr(provider, '_reason', 'not_checked')
    monkeypatch.setattr(provider, '_ready', False)


def fake_client(callback):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=callback)))


def test_optional_reasoning_setting_is_forwarded_for_hosted_instruct_models(monkeypatch):
    monkeypatch.setattr(provider.settings, 'LLM_REASONING_EFFORT', 'none')
    calls = []
    def completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Reply'))])
    assert provider.generate([], fake_client(completion)) == ('Reply', True)
    assert calls[0]['reasoning_effort'] == 'none'


def test_settings_read_chat_config_from_dotenv(tmp_path):
    env = tmp_path / '.env'
    env.write_text('DB_URL=postgresql://test\nACCESS_TOKEN_SECRET_KEY=test\n'
                   'REFRESH_TOKEN_SECRET_KEY=test\nALGORITHM=HS256\n'
                   'LLM_ENABLED=false\nLLM_MODEL=local-test\nLLM_TIMEOUT=7\nOTHER_SETTING=ignored\n')
    config = Settings(_env_file=env)
    assert config.LLM_ENABLED is False
    assert config.LLM_MODEL == 'local-test'
    assert config.LLM_TIMEOUT == 7


def test_provider_failure_returns_fallback_and_skips_repeated_wait():
    calls = []
    def offline(**kwargs):
        calls.append(kwargs)
        raise httpx.ConnectError('private endpoint details')
    client = fake_client(offline)
    assert provider.generate([{'role': 'user', 'content': 'hello'}], client) == (None, False)
    assert provider.generate([], client) == (None, False)
    assert len(calls) == 1
    assert provider._reason == 'offline'


def test_successful_model_output_and_empty_response():
    good = fake_client(lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='  Reply  '))]))
    assert provider.generate([], good) == ('Reply', True)
    assert provider._ready
    empty = fake_client(lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=' '))]))
    assert provider.generate([], empty) == (None, False)
    assert provider._reason == 'empty_response'


def test_busy_provider_does_not_queue_more_requests():
    provider._generation_lock.acquire()
    try:
        assert provider.generate([], fake_client(lambda **kw: pytest.fail('Should not call model'))) == (None, False)
    finally:
        provider._generation_lock.release()


def test_model_probe_reports_missing_model_without_exposing_key(monkeypatch):
    def serve(request):
        assert request.url.path.endswith('/models')
        return httpx.Response(200, json={'data': [{'id': 'another-model'}]})
    real_client = httpx.Client
    monkeypatch.setattr(provider, 'client', object())
    monkeypatch.setattr(provider.httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(serve), **kwargs))
    status = provider.status(probe=True)
    assert not status['ready']
    assert status['reason'] == 'model_missing'
    assert set(status) == {'ready', 'reason', 'model'}
