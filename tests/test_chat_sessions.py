import pytest
from fastapi import HTTPException
from chatbot import sessions


def test_repeated_reads_load_once_and_do_not_expose_mutable_cache():
    calls = []
    @sessions.cached_read
    def profile(student_id):
        calls.append(student_id)
        return {'name': 'Student'}
    session = sessions.create(1, 10)
    with sessions.use(session):
        profile(10)['name'] = 'changed'
    with sessions.use(session):
        assert profile(10)['name'] == 'Student'
    assert calls == [10]


def test_mutations_invalidate_snapshot_on_next_message():
    calls = []
    @sessions.cached_read
    def read(student_id):
        calls.append(student_id)
        return len(calls)
    session = sessions.create(1, 10)
    with sessions.use(session):
        assert read(10) == 1
    sessions.invalidate()
    with sessions.use(session):
        assert read(10) == 2


def test_session_cannot_be_shared_between_accounts():
    session = sessions.create(1, 10)
    for owner, student in [(2, 10), (1, 11)]:
        with pytest.raises(HTTPException) as exc:
            sessions.get(session.id, owner, student)
        assert exc.value.status_code == 403


def test_expired_session_is_removed():
    session = sessions.create(1, 10)
    session.touched -= sessions.TTL_SECONDS + 1
    with pytest.raises(HTTPException) as exc:
        sessions.get(session.id, 1, 10)
    assert exc.value.status_code == 410


def test_cache_size_is_bounded(monkeypatch):
    monkeypatch.setattr(sessions, 'MAX_SESSIONS', 2)
    sessions.create(1, 10)
    sessions.create(2, 11)
    newest = sessions.create(3, 12)
    assert len(sessions._sessions) <= 2
    assert sessions.get(newest.id, 3, 12) is newest


def test_chat_reuses_snapshot_and_remembers_conversation(monkeypatch):
    from routers import chatbot
    calls = []
    for name, result in [('get_student_profile', {'student_id': 10}),
                         ('get_muscle_fatigue', {'muscles': {}}),
                         ('get_progress_stats', {'total_interactions': 0}),
                         ('get_interaction_history', []), ('get_latest_plan', None)]:
        def make_reader(name, result):
            def reader(*args, **kwargs):
                calls.append(name)
                return result
            reader.__name__ = name
            return sessions.cached_read(reader)
        monkeypatch.setattr(chatbot, name, make_reader(name, result))
    monkeypatch.setattr(chatbot, 'llm_client', None)
    user = {'user_id': 1, 'student_id': 10, 'role': 'student'}
    started = chatbot.start_session(user)
    assert len(calls) == 5
    for text in ['hello', 'thanks']:
        response = chatbot.chat(chatbot.ChatMessage(text=text, session_id=started['session_id']), user)
        assert response.session_id == started['session_id']
    assert len(calls) == 5
    assert len(sessions.get(started['session_id'], 1, 10).history) == 4
