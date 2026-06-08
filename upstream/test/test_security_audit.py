from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from open_webui.utils.audit import AuditLevel, AuditLogger, AuditLoggingMiddleware, set_audit_event


class DummyUser:
    def __init__(self, id='user-id', email='user@example.com', name='User', role='user'):
        self.id = id
        self.email = email
        self.name = name
        self.role = role

    def model_dump(self, include=None, **kwargs):
        data = {'id': self.id, 'email': self.email, 'name': self.name, 'role': self.role}
        if include:
            return {key: value for key, value in data.items() if key in include}
        return data


def _user_from_request(request: Request) -> DummyUser:
    auth = request.headers.get('Authorization', '')
    if auth == 'Bearer admin-token':
        return DummyUser(id='admin-id', email='admin@example.com', name='Admin', role='admin')
    if auth == 'Bearer user-token':
        return DummyUser(id='user-id', email='user@example.com', name='User', role='user')
    if auth == 'Bearer curator-token':
        return DummyUser(id='curator-id', email='curator@example.com', name='Curator', role='security_curator')
    if auth == 'Bearer sk-service-key':
        return DummyUser(id='svc-id', email='svc@example.com', name='Service', role='user')
    if request.cookies.get('token') == 'cookie-token':
        return DummyUser(id='cookie-id', email='cookie@example.com', name='Cookie User', role='user')
    raise HTTPException(status_code=401, detail='Not authenticated')


async def _fake_get_current_user(request, response=None, background_tasks=None, auth_token=None):
    return _user_from_request(request)


def _require_admin(request: Request):
    user = _user_from_request(request)
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail='Forbidden')
    return user


def _build_app(monkeypatch):
    entries = []
    monkeypatch.setattr('open_webui.utils.audit.get_current_user', _fake_get_current_user)
    monkeypatch.setattr(AuditLogger, 'write', lambda self, entry, **kwargs: entries.append(entry))

    app = FastAPI()

    @app.post('/api/v1/auths/signin')
    async def signin(request: Request, payload: dict):
        if payload.get('email') == 'user@example.com' and payload.get('password') == 'correct':
            user = DummyUser()
            set_audit_event(
                request,
                'auth.login.success',
                outcome='success',
                actor=user.model_dump(include={'id', 'name', 'email', 'role'}),
                target={'id': user.id, 'email': user.email},
            )
            return {'token': 'secret-token', 'token_type': 'Bearer'}
        raise HTTPException(status_code=400, detail='Invalid credentials')

    @app.post('/api/v1/auths/signup')
    async def signup(request: Request, payload: dict):
        user = DummyUser(id='new-id', email=payload['email'], name=payload['name'], role='user')
        set_audit_event(
            request,
            'auth.signup',
            outcome='success',
            actor=user.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'id': user.id, 'email': user.email},
            changes={'created': {'email': user.email, 'name': user.name, 'role': user.role}},
        )
        return {'token': 'signup-token', 'email': user.email}

    @app.post('/api/v1/auths/signout')
    async def signout(request: Request):
        user = _user_from_request(request)
        set_audit_event(
            request,
            'auth.logout',
            outcome='success',
            actor=user.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'id': user.id, 'email': user.email},
        )
        return {'status': True}

    @app.post('/api/v1/auths/add')
    async def add_user(request: Request, payload: dict, admin=Depends(_require_admin)):
        set_audit_event(
            request,
            'user.created',
            outcome='success',
            actor=admin.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'id': 'created-id', 'email': payload['email']},
            changes={'created': {'email': payload['email'], 'role': payload.get('role')}},
        )
        return {'id': 'created-id', 'token': 'new-user-token'}

    @app.delete('/api/v1/users/{user_id}')
    async def delete_user(request: Request, user_id: str, admin=Depends(_require_admin)):
        set_audit_event(
            request,
            'user.deleted',
            outcome='success',
            actor=admin.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'id': user_id},
        )
        return True

    @app.post('/api/v1/users/{user_id}/update')
    async def update_user(request: Request, user_id: str, payload: dict, admin=Depends(_require_admin)):
        event_type = 'user.role.changed' if 'role' in payload else 'user.updated'
        set_audit_event(
            request,
            event_type,
            outcome='success',
            actor=admin.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'id': user_id, 'email': payload.get('email')},
            changes={'requested': payload},
        )
        return {'id': user_id, **payload}

    @app.post('/api/v1/users/default/permissions')
    async def default_permissions(request: Request, payload: dict, admin=Depends(_require_admin)):
        set_audit_event(
            request,
            'permissions.default.updated',
            outcome='success',
            actor=admin.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'type': 'default_user_permissions'},
            changes={'to': payload},
        )
        return payload

    def _require_admin_read(request: Request):
        user = _user_from_request(request)
        if user.role not in {'admin', 'security_curator'}:
            raise HTTPException(status_code=403, detail='Forbidden')
        return user

    @app.get('/api/v1/users/')
    async def admin_users(admin=Depends(_require_admin_read)):
        return {'users': []}

    @app.post('/api/v1/auths/api_key')
    async def create_api_key(request: Request):
        user = _user_from_request(request)
        set_audit_event(
            request,
            'api_key.created',
            outcome='success',
            actor=user.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'id': user.id},
        )
        return {'api_key': 'sk-response-secret'}

    app.add_middleware(AuditLoggingMiddleware, audit_level=AuditLevel.REQUEST_RESPONSE)
    return app, entries


def test_login_success(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).post('/api/v1/auths/signin', json={'email': 'user@example.com', 'password': 'correct'})

    assert response.status_code == 200
    assert entries[-1].event_type == 'auth.login.success'
    assert entries[-1].outcome == 'success'
    assert entries[-1].target == {'id': 'user-id', 'email': 'user@example.com'}


def test_login_failed(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).post('/api/v1/auths/signin', json={'email': 'user@example.com', 'password': 'wrong'})

    assert response.status_code == 400
    assert entries[-1].event_type == 'auth.login.failed'
    assert entries[-1].outcome == 'failure'
    assert entries[-1].target == {'email': 'user@example.com'}
    assert entries[-1].request_object['password'] == '********'


def test_logout(monkeypatch):
    app, entries = _build_app(monkeypatch)
    client = TestClient(app)
    client.cookies.set('token', 'cookie-token')
    response = client.post('/api/v1/auths/signout')

    assert response.status_code == 200
    assert entries[-1].event_type == 'auth.logout'
    assert entries[-1].auth_method == 'cookie'


def test_admin_creates_user(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).post(
        '/api/v1/auths/add',
        headers={'Authorization': 'Bearer admin-token'},
        json={'email': 'created@example.com', 'password': 'Secret123', 'name': 'Created', 'role': 'user'},
    )

    assert response.status_code == 200
    assert entries[-1].event_type == 'user.created'
    assert entries[-1].target['email'] == 'created@example.com'


def test_admin_deletes_user(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).delete('/api/v1/users/target-id', headers={'Authorization': 'Bearer admin-token'})

    assert response.status_code == 200
    assert entries[-1].event_type == 'user.deleted'
    assert entries[-1].target == {'id': 'target-id'}


def test_admin_changes_user_role(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).post(
        '/api/v1/users/target-id/update',
        headers={'Authorization': 'Bearer admin-token'},
        json={'role': 'admin'},
    )

    assert response.status_code == 200
    assert entries[-1].event_type == 'user.role.changed'
    assert entries[-1].changes == {'requested': {'role': 'admin'}}


def test_admin_changes_default_permissions(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).post(
        '/api/v1/users/default/permissions',
        headers={'Authorization': 'Bearer admin-token'},
        json={'features': {'api_keys': True}},
    )

    assert response.status_code == 200
    assert entries[-1].event_type == 'permissions.default.updated'
    assert entries[-1].target == {'type': 'default_user_permissions'}


def test_non_admin_receives_403_on_admin_endpoint(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).get('/api/v1/users/', headers={'Authorization': 'Bearer user-token'})

    assert response.status_code == 403
    assert entries[-1].event_type == 'access.denied.forbidden'
    assert entries[-1].outcome == 'failure'


def test_security_curator_can_read_admin_get(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).get('/api/v1/users/', headers={'Authorization': 'Bearer curator-token'})

    assert response.status_code == 200


def test_security_curator_write_attempt_receives_403_and_is_audited(monkeypatch):
    app, entries = _build_app(monkeypatch)
    response = TestClient(app).delete('/api/v1/users/target-id', headers={'Authorization': 'Bearer curator-token'})

    assert response.status_code == 403
    assert entries[-1].event_type == 'access.denied.security_curator_write_attempt'
    assert entries[-1].actor_type == 'user'


def test_audit_log_redacts_password_token_and_api_key(monkeypatch):
    app, entries = _build_app(monkeypatch)
    client = TestClient(app)
    client.post('/api/v1/auths/signin', json={'email': 'user@example.com', 'password': 'correct'})
    client.post('/api/v1/auths/api_key', headers={'Authorization': 'Bearer sk-service-key'})

    login_entry = next(entry for entry in entries if entry.event_type == 'auth.login.success')
    api_key_entry = next(entry for entry in entries if entry.event_type == 'api_key.created')
    assert login_entry.request_object['password'] == '********'
    assert login_entry.response_object['token'] == '********'
    assert api_key_entry.response_object['api_key'] == '********'
    assert 'secret-token' not in str(login_entry)
    assert 'sk-response-secret' not in str(api_key_entry)


def test_audit_retention_config_is_applied(monkeypatch, tmp_path):
    from open_webui.utils import logger as logger_module

    add_calls = []
    monkeypatch.setattr(logger_module, 'AUDIT_LOG_LEVEL', 'METADATA')
    monkeypatch.setattr(logger_module, 'ENABLE_AUDIT_LOGS_FILE', True)
    monkeypatch.setattr(logger_module, 'ENABLE_AUDIT_STDOUT', False)
    monkeypatch.setattr(logger_module, 'AUDIT_LOGS_FILE_PATH', str(tmp_path / 'audit.log'))
    monkeypatch.setattr(logger_module, 'AUDIT_LOG_RETENTION_DAYS', 7)
    monkeypatch.setattr(logger_module.logger, 'add', lambda *args, **kwargs: add_calls.append(kwargs) or len(add_calls))

    logger_module.start_logger()

    audit_file_call = next(
        call for call in add_calls if call.get('rotation') == logger_module.AUDIT_LOG_FILE_ROTATION_SIZE
    )
    assert audit_file_call['retention'] == '7 days'


def test_audit_retention_days_parser_defaults_invalid_values():
    from open_webui.env import parse_audit_log_retention_days

    assert parse_audit_log_retention_days('30') == 30
    assert parse_audit_log_retention_days('') == 365
    assert parse_audit_log_retention_days('invalid') == 365
    assert parse_audit_log_retention_days('-1') == 365


def _build_security_router_app(monkeypatch, tmp_path):
    from open_webui.routers import security as security_router

    audit_log_path = tmp_path / 'audit.log'
    monkeypatch.setattr(security_router, 'AUDIT_LOGS_FILE_PATH', str(audit_log_path))
    monkeypatch.setattr(security_router, 'AUDIT_LOG_LEVEL', 'REQUEST_RESPONSE')
    monkeypatch.setattr(security_router, 'ENABLE_AUDIT_LOGS_FILE', True)
    monkeypatch.setattr(security_router, 'ENABLE_AUDIT_STDOUT', False)
    monkeypatch.setattr(security_router, 'AUDIT_LOG_FILE_ROTATION_SIZE', '10MB')
    monkeypatch.setattr(security_router, 'AUDIT_LOG_RETENTION_DAYS', 365)
    monkeypatch.setattr(security_router, 'AUDIT_INCLUDED_PATHS', [])
    monkeypatch.setattr(security_router, 'AUDIT_EXCLUDED_PATHS', [])
    monkeypatch.setattr(security_router, 'ENABLE_AUDIT_GET_REQUESTS', False)
    monkeypatch.setattr(security_router, 'MAX_BODY_LOG_SIZE', 2048)
    monkeypatch.setattr(security_router, 'OFFLINE_MODE', True)
    monkeypatch.setattr(security_router, 'ENABLE_VERSION_UPDATE_CHECK', True)

    async def _security_read_user(request: Request):
        auth = request.headers.get('Authorization', '')
        if auth == 'Bearer admin-token':
            return DummyUser(id='admin-id', email='admin@example.com', name='Admin', role='admin')
        if auth == 'Bearer curator-token':
            return DummyUser(id='curator-id', email='curator@example.com', name='Curator', role='security_curator')
        if auth in {'Bearer user-token', 'Bearer pending-token'}:
            raise HTTPException(status_code=403, detail='Forbidden')
        raise HTTPException(status_code=401, detail='Not authenticated')

    app = FastAPI()
    app.state.config = SimpleNamespace(
        ENABLE_OLLAMA_API=False,
        OLLAMA_BASE_URLS=[],
        OLLAMA_API_CONFIGS={},
        OPENAI_API_BASE_URLS=[],
    )
    app.dependency_overrides[security_router.get_admin_or_security_curator_user] = _security_read_user
    app.include_router(security_router.router, prefix='/api/v1/admin/security')
    return app, audit_log_path


def test_security_audit_status_rbac(monkeypatch, tmp_path):
    app, _ = _build_security_router_app(monkeypatch, tmp_path)
    client = TestClient(app)

    assert (
        client.get('/api/v1/admin/security/audit/status', headers={'Authorization': 'Bearer admin-token'}).status_code
        == 200
    )
    assert (
        client.get('/api/v1/admin/security/audit/status', headers={'Authorization': 'Bearer curator-token'}).status_code
        == 200
    )
    assert (
        client.get('/api/v1/admin/security/audit/status', headers={'Authorization': 'Bearer user-token'}).status_code
        == 403
    )
    assert (
        client.get('/api/v1/admin/security/audit/status', headers={'Authorization': 'Bearer pending-token'}).status_code
        == 403
    )


def test_security_audit_logs_absent_file_returns_empty(monkeypatch, tmp_path):
    app, _ = _build_security_router_app(monkeypatch, tmp_path)
    response = TestClient(app).get(
        '/api/v1/admin/security/audit/logs',
        headers={'Authorization': 'Bearer curator-token'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['items'] == []
    assert body['file_exists'] is False
    assert body['total_returned'] == 0


def test_security_audit_logs_skip_invalid_json_and_redact(monkeypatch, tmp_path):
    app, audit_log_path = _build_security_router_app(monkeypatch, tmp_path)
    audit_log_path.write_text(
        '\n'.join(
            [
                json.dumps(
                    {
                        'timestamp': 1760000000,
                        'event_type': 'auth.login.success',
                        'outcome': 'success',
                        'actor': {'id': 'admin-id', 'role': 'admin', 'email': 'admin@example.com'},
                        'request_object': {'password': 'secret-password'},
                        'response_object': {'token': 'secret-token', 'api_key': 'sk-secret'},
                    }
                ),
                'not-json',
            ]
        ),
        encoding='utf-8',
    )

    response = TestClient(app).get(
        '/api/v1/admin/security/audit/logs',
        headers={'Authorization': 'Bearer admin-token'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['file_exists'] is True
    assert body['total_returned'] == 1
    assert body['items'][0]['request_object']['password'] == '********'
    assert body['items'][0]['response_object']['token'] == '********'
    assert body['items'][0]['response_object']['api_key'] == '********'
    assert 'secret-password' not in str(body)
    assert 'secret-token' not in str(body)
    assert 'sk-secret' not in str(body)


def test_security_audit_logs_limit_is_capped(monkeypatch, tmp_path):
    app, audit_log_path = _build_security_router_app(monkeypatch, tmp_path)
    audit_log_path.write_text(
        '\n'.join(json.dumps({'timestamp': idx, 'event_type': 'test.event'}) for idx in range(1005)),
        encoding='utf-8',
    )

    response = TestClient(app).get(
        '/api/v1/admin/security/audit/logs?limit=5000',
        headers={'Authorization': 'Bearer admin-token'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['limit'] == 1000
    assert body['total_returned'] == 1000


def test_security_audit_logs_does_not_accept_path_traversal(monkeypatch, tmp_path):
    app, audit_log_path = _build_security_router_app(monkeypatch, tmp_path)
    audit_log_path.write_text(json.dumps({'event_type': 'configured.file'}) + '\n', encoding='utf-8')

    response = TestClient(app).get(
        '/api/v1/admin/security/audit/logs?path=/etc/passwd',
        headers={'Authorization': 'Bearer admin-token'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['file_exists'] is True
    assert body['items'][0]['event_type'] == 'configured.file'
    assert 'root:' not in str(body)


def test_security_versions_rbac_and_offline_mode(monkeypatch, tmp_path):
    app, _ = _build_security_router_app(monkeypatch, tmp_path)
    client = TestClient(app)

    admin_response = client.get('/api/v1/admin/security/versions', headers={'Authorization': 'Bearer admin-token'})
    curator_response = client.get('/api/v1/admin/security/versions', headers={'Authorization': 'Bearer curator-token'})
    user_response = client.get('/api/v1/admin/security/versions', headers={'Authorization': 'Bearer user-token'})

    assert admin_response.status_code == 200
    assert curator_response.status_code == 200
    assert user_response.status_code == 403
    assert admin_response.json()['offline_mode'] is True
    assert admin_response.json()['latest_available_version'] is None
