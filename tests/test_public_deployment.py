import pytest
from fastapi import HTTPException
import auth


def test_public_deployment_cannot_claim_unregistered_student_profile(monkeypatch):
    monkeypatch.setattr(auth.settings, 'PUBLIC_REGISTRATION_ENABLED', False)
    monkeypatch.setattr(auth, 'get_connection', lambda: pytest.fail('No database access expected'))
    with pytest.raises(HTTPException) as exc:
        auth.register(auth.RegisterRequest(email='other@example.com', password='test', student_id=10))
    assert exc.value.status_code == 403
    assert auth.public_auth_config() == {'registration_enabled': False}
