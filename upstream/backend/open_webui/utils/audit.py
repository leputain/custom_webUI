import re
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    MutableMapping,
    Optional,
    cast,
)

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGIReceiveEvent,
    ASGISendCallable,
    ASGISendEvent,
)
from asgiref.typing import (
    Scope as ASGIScope,
)
from loguru import logger
from open_webui.env import (
    AUDIT_INCLUDED_PATHS,
    CUSTOM_API_KEY_HEADER,
    ENABLE_AUDIT_GET_REQUESTS,
    MAX_BODY_LOG_SIZE,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
)
from open_webui.models.users import UserModel
from open_webui.utils.auth import SECURITY_CURATOR_ROLE, get_current_user, get_http_authorization_cred
from starlette.requests import Request

if TYPE_CHECKING:
    from loguru import Logger


@dataclass(frozen=True)
class AuditLogEntry:
    # `Metadata` audit level properties
    id: str
    user: Optional[dict[str, Any]]
    audit_level: str
    verb: str
    request_uri: str
    user_agent: Optional[str] = None
    source_ip: Optional[str] = None
    # `Request` audit level properties
    request_object: Any = None
    # `Request Response` level
    response_object: Any = None
    response_status_code: Optional[int] = None
    # Semantic security audit properties
    event_type: str = 'http.request'
    outcome: str = 'unknown'
    actor: Optional[dict[str, Any]] = None
    target: Optional[dict[str, Any]] = None
    changes: Optional[dict[str, Any]] = None
    request_id: Optional[str] = None
    auth_method: str = 'unknown'
    actor_type: str = 'unknown'


class AuditLevel(str, Enum):
    NONE = 'NONE'
    METADATA = 'METADATA'
    REQUEST = 'REQUEST'
    REQUEST_RESPONSE = 'REQUEST_RESPONSE'


REDACTED = '********'
SENSITIVE_FIELD_NAMES = {
    'api_key',
    'apikey',
    'authorization',
    'cookie',
    'cookies',
    'credential',
    'credentials',
    'id_token',
    'key',
    'logout_token',
    'new_password',
    'password',
    'refresh_token',
    'secret',
    'token',
}


def _is_sensitive_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.lower().replace('-', '_').replace(' ', '_')
    return normalized in SENSITIVE_FIELD_NAMES or normalized.endswith('_token') or normalized.endswith('_secret')


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: REDACTED if _is_sensitive_key(key) else redact_sensitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        redacted = re.sub(r'(?i)(bearer\s+)[a-z0-9._~+/=-]+', rf'\1{REDACTED}', value)
        redacted = re.sub(r'(?i)(sk-)[a-z0-9_-]+', rf'\1{REDACTED}', redacted)
        redacted = re.sub(
            r'(?i)("?(?:password|new_password|token|api_key|authorization|cookie|secret)"?\s*[:=]\s*)"[^"]*"',
            lambda match: f'{match.group(1)}"{REDACTED}"',
            redacted,
        )
        return redacted
    return value


def parse_and_redact_body(body: str) -> Any:
    if not body:
        return None

    try:
        return redact_sensitive(json.loads(body))
    except Exception:
        return redact_sensitive(body)


def set_audit_event(
    request: Request,
    event_type: str,
    *,
    outcome: Optional[str] = None,
    target: Optional[dict[str, Any]] = None,
    changes: Optional[dict[str, Any]] = None,
    actor: Optional[dict[str, Any]] = None,
    actor_type: Optional[str] = None,
    auth_method: Optional[str] = None,
) -> None:
    request.state.audit_event = {
        'event_type': event_type,
        **({'outcome': outcome} if outcome else {}),
        **({'target': redact_sensitive(target)} if target is not None else {}),
        **({'changes': redact_sensitive(changes)} if changes is not None else {}),
        **({'actor': redact_sensitive(actor)} if actor is not None else {}),
        **({'actor_type': actor_type} if actor_type else {}),
        **({'auth_method': auth_method} if auth_method else {}),
    }


def changed_fields(before: Optional[dict[str, Any]], after: Optional[dict[str, Any]]) -> dict[str, Any]:
    before = before or {}
    after = after or {}
    changes = {}
    for key, new_value in after.items():
        old_value = before.get(key)
        if old_value != new_value:
            changes[key] = {
                'from': redact_sensitive(old_value),
                'to': redact_sensitive(new_value),
            }
    return changes


class AuditLogger:
    """
    A helper class that encapsulates audit logging functionality. It uses Loguru’s logger with an auditable binding to ensure that audit log entries are filtered correctly.

    Parameters:
    logger (Logger): An instance of Loguru’s logger.
    """

    def __init__(self, logger: 'Logger'):
        self.logger = logger.bind(auditable=True)

    def write(
        self,
        audit_entry: AuditLogEntry,
        *,
        log_level: str = 'INFO',
        extra: Optional[dict] = None,
    ):
        entry = asdict(audit_entry)

        if extra:
            entry['extra'] = extra

        self.logger.log(
            log_level,
            '',
            **entry,
        )


class AuditContext:
    """
    Captures and aggregates the HTTP request and response bodies during the processing of a request. It ensures that only a configurable maximum amount of data is stored to prevent excessive memory usage.

    Attributes:
    request_body (bytearray): Accumulated request payload.
    response_body (bytearray): Accumulated response payload.
    max_body_size (int): Maximum number of bytes to capture.
    metadata (Dict[str, Any]): A dictionary to store additional audit metadata (user, http verb, user agent, etc.).
    """

    def __init__(self, max_body_size: int = MAX_BODY_LOG_SIZE):
        self.request_body = bytearray()
        self.response_body = bytearray()
        self.max_body_size = max_body_size
        self.metadata: Dict[str, Any] = {}

    def add_request_chunk(self, chunk: bytes):
        if len(self.request_body) < self.max_body_size:
            self.request_body.extend(chunk[: self.max_body_size - len(self.request_body)])

    def add_response_chunk(self, chunk: bytes):
        if len(self.response_body) < self.max_body_size:
            self.response_body.extend(chunk[: self.max_body_size - len(self.response_body)])


class AuditLoggingMiddleware:
    """
    ASGI middleware that intercepts HTTP requests and responses to perform audit logging. It captures request/response bodies (depending on audit level), headers, HTTP methods, and user information, then logs a structured audit entry at the end of the request cycle.
    """

    DEFAULT_AUDITED_METHODS = {'PUT', 'PATCH', 'DELETE', 'POST'}
    ALWAYS_LOG_ENDPOINTS = {
        '/api/v1/auths/signin',
        '/api/v1/auths/ldap',
        '/api/v1/auths/signout',
        '/api/v1/auths/signup',
        '/api/v1/auths/add',
        '/api/v1/users/default/permissions',
        '/api/v1/admin/security/audit/status',
        '/api/v1/admin/security/audit/logs',
        '/api/v1/admin/security/versions',
    }
    ALWAYS_LOG_PREFIXES = (
        '/api/v1/users/',
        '/api/v1/groups/',
        '/api/v1/models/model/access/update',
        '/api/v1/knowledge/',
        '/api/v1/tools/id/',
    )

    def __init__(
        self,
        app: ASGI3Application,
        *,
        excluded_paths: Optional[list[str]] = None,
        included_paths: Optional[list[str]] = None,
        max_body_size: int = MAX_BODY_LOG_SIZE,
        audit_level: AuditLevel = AuditLevel.NONE,
        audit_get_requests: bool = False,
    ) -> None:
        self.app = app
        self.audit_logger = AuditLogger(logger)
        self.excluded_paths = excluded_paths or []
        self.included_paths = included_paths or []
        self.max_body_size = max_body_size
        self.audited_methods = set(self.DEFAULT_AUDITED_METHODS)
        if audit_get_requests:
            self.audited_methods.add('GET')
        self.audit_level = audit_level

        if self.included_paths and self.excluded_paths:
            logger.warning(
                'Both AUDIT_INCLUDED_PATHS and AUDIT_EXCLUDED_PATHS are set. '
                'AUDIT_INCLUDED_PATHS (whitelist) takes precedence.'
            )

    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        request = Request(scope=cast(MutableMapping, scope))

        if self._should_skip_auditing(request):
            return await self.app(scope, receive, send)

        async with self._audit_context(request) as context:
            capture_request_body = self.audit_level in (
                AuditLevel.REQUEST,
                AuditLevel.REQUEST_RESPONSE,
            ) or self._is_semantic_audit_path(request)

            async def send_wrapper(message: ASGISendEvent) -> None:
                if message['type'] == 'http.response.start':
                    context.metadata['response_status_code'] = message['status']

                if self.audit_level == AuditLevel.REQUEST_RESPONSE:
                    await self._capture_response(message, context)

                await send(message)

            original_receive = receive

            async def receive_wrapper() -> ASGIReceiveEvent:
                nonlocal original_receive
                message = await original_receive()

                if capture_request_body:
                    await self._capture_request(message, context)

                return message

            await self.app(scope, receive_wrapper, send_wrapper)

    @asynccontextmanager
    async def _audit_context(self, request: Request) -> AsyncGenerator[AuditContext, None]:
        """
        async context manager that ensures that an audit log entry is recorded after the request is processed.
        """
        context = AuditContext()
        try:
            yield context
        finally:
            await self._log_audit_entry(request, context)

    async def _get_authenticated_user(self, request: Request) -> Optional[UserModel]:
        auth_header = request.headers.get('Authorization')

        try:
            user = await get_current_user(request, None, None, get_http_authorization_cred(auth_header))
            return user
        except Exception as e:
            logger.debug(f'Failed to get authenticated user: {str(e)}')

        return None

    def _should_skip_auditing(self, request: Request) -> bool:
        if self.audit_level == AuditLevel.NONE:
            return True

        path = request.url.path.lower()
        for endpoint in self.ALWAYS_LOG_ENDPOINTS:
            if path.startswith(endpoint):
                return False  # Do NOT skip logging for auth endpoints

        if self._is_semantic_audit_path(request):
            return False

        if request.method not in self.audited_methods:
            return True

        # Whitelist mode: only log paths that match included_paths
        if self.included_paths:
            pattern = re.compile(r'^/api(?:/v1)?/(' + '|'.join(self.included_paths) + r')\b')
            if not pattern.match(request.url.path):
                return True  # Skip: path not in whitelist
            return False  # Do NOT skip: path is in whitelist

        # Blacklist mode: skip paths that match excluded_paths
        if self.excluded_paths:
            pattern = re.compile(r'^/api(?:/v1)?/(' + '|'.join(self.excluded_paths) + r')\b')
            if pattern.match(request.url.path):
                return True

        return False

    def _is_semantic_audit_path(self, request: Request) -> bool:
        path = request.url.path.lower()
        if any(path.startswith(endpoint) for endpoint in self.ALWAYS_LOG_ENDPOINTS):
            return True
        if any(path.startswith(prefix) for prefix in self.ALWAYS_LOG_PREFIXES):
            return True
        return '/access/update' in path

    async def _capture_request(self, message: ASGIReceiveEvent, context: AuditContext):
        if message['type'] == 'http.request':
            body = message.get('body', b'')
            context.add_request_chunk(body)

    async def _capture_response(self, message: ASGISendEvent, context: AuditContext):
        if message['type'] == 'http.response.body':
            body = message.get('body', b'')
            context.add_response_chunk(body)

    def _get_auth_method(self, request: Request) -> str:
        path = request.url.path.lower()
        if path.startswith('/oauth/') or request.cookies.get('oauth_session_id') or request.cookies.get('oauth_id_token'):
            return 'oauth'
        if WEBUI_AUTH_TRUSTED_EMAIL_HEADER and request.headers.get(WEBUI_AUTH_TRUSTED_EMAIL_HEADER):
            return 'trusted_header'
        custom_api_key = request.headers.get(CUSTOM_API_KEY_HEADER)
        if custom_api_key:
            return 'api_key'
        auth_header = request.headers.get('Authorization')
        auth_cred = get_http_authorization_cred(auth_header)
        if auth_cred:
            if auth_cred.credentials.startswith('sk-'):
                return 'api_key'
            return 'jwt'
        if request.cookies.get('token'):
            return 'cookie'
        token = getattr(request.state, 'token', None)
        if token and getattr(token, 'credentials', '').startswith('sk-'):
            return 'api_key'
        return 'unknown'

    def _get_actor_type(self, user: dict[str, Any], auth_method: str, override: Optional[str] = None) -> str:
        if override in {'admin', 'user', 'service_account', 'api_key', 'unknown'}:
            return override
        if auth_method == 'api_key':
            return 'api_key'
        role = user.get('role') if user else None
        if role == 'admin':
            return 'admin'
        if role in {'user', SECURITY_CURATOR_ROLE}:
            return 'user'
        return 'unknown'

    def _get_outcome(self, status_code: Optional[int]) -> str:
        if status_code is None:
            return 'unknown'
        if status_code < 400:
            return 'success'
        if status_code >= 500:
            return 'error'
        return 'failure'

    def _infer_event_type(self, request: Request, status_code: Optional[int], user: dict[str, Any]) -> str:
        path = request.url.path.lower()
        method = request.method.upper()

        if path.startswith('/api/v1/auths/signin'):
            return 'auth.login.success' if status_code and status_code < 400 else 'auth.login.failed'
        if path.startswith('/api/v1/auths/ldap'):
            return 'auth.ldap.login.success' if status_code and status_code < 400 else 'auth.ldap.login.failed'
        if status_code == 401:
            return 'access.denied.unauthorized'
        if status_code == 403:
            if user.get('role') == SECURITY_CURATOR_ROLE and method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
                return 'access.denied.security_curator_write_attempt'
            if self._get_auth_method(request) == 'api_key':
                return 'auth.api_key.denied'
            if self._is_semantic_audit_path(request) and user.get('role') != 'admin':
                return 'access.denied.forbidden'
            return 'access.denied.forbidden'
        if path.startswith('/api/v1/auths/signout'):
            return 'auth.logout'
        if path.startswith('/api/v1/auths/signup'):
            return 'auth.signup'
        if path.startswith('/api/v1/auths/add'):
            return 'user.created'
        if path.startswith('/api/v1/auths/api_key'):
            return 'api_key.deleted' if method == 'DELETE' else 'api_key.created'
        if path.startswith('/api/v1/users/default/permissions'):
            return 'permissions.default.updated'
        if re.match(r'^/api/v1/users/[^/]+/update$', path):
            return 'user.updated'
        if method == 'DELETE' and re.match(r'^/api/v1/users/[^/]+$', path):
            return 'user.deleted'
        if re.match(r'^/api/v1/groups/[^/]+/users/(add|remove)$', path) or re.match(
            r'^/api/v1/groups/id/[^/]+/users/(add|remove)$', path
        ):
            return 'user.groups.updated'
        if '/access/update' in path:
            return 'access_grants.updated'
        return 'http.request'

    def _infer_target(self, request: Request, request_object: Any) -> dict[str, Any]:
        path = request.url.path
        body = request_object if isinstance(request_object, dict) else {}

        if path.startswith('/api/v1/auths/signin'):
            return {'email': body.get('email')}
        if path.startswith('/api/v1/auths/ldap'):
            return {'username': body.get('user')}
        if path.startswith('/api/v1/auths/signup') or path.startswith('/api/v1/auths/add'):
            return {'email': body.get('email')}
        user_match = re.match(r'^/api/v1/users/([^/]+)', path)
        if user_match and user_match.group(1) not in {'default', 'user', 'groups', 'permissions', 'search', 'all'}:
            return {'id': user_match.group(1), **({'email': body.get('email')} if body.get('email') else {})}
        group_match = re.match(r'^/api/v1/groups/id/([^/]+)', path)
        if group_match:
            return {'type': 'group', 'id': group_match.group(1)}
        if '/access/update' in path:
            resource_type = 'unknown'
            if '/models/' in path:
                resource_type = 'model'
            elif '/knowledge/' in path:
                resource_type = 'knowledge'
            elif '/tools/' in path:
                resource_type = 'tool'
            return {'type': resource_type, **({'id': body.get('id')} if body.get('id') else {})}
        return {}

    def _infer_changes(self, request: Request, request_object: Any) -> dict[str, Any]:
        path = request.url.path.lower()
        body = request_object if isinstance(request_object, dict) else {}
        if not body:
            return {}
        if path.startswith('/api/v1/auths/signin') or path.startswith('/api/v1/auths/ldap'):
            return {}
        if path.startswith('/api/v1/auths/signup') or path.startswith('/api/v1/auths/add'):
            return {'created': redact_sensitive(body)}
        if path.startswith('/api/v1/users/default/permissions') or '/access/update' in path:
            return {'to': redact_sensitive(body)}
        if re.match(r'^/api/v1/users/[^/]+/update$', path):
            return {'requested': redact_sensitive(body)}
        if '/users/add' in path:
            return {'added_user_ids': body.get('user_ids', [])}
        if '/users/remove' in path:
            return {'removed_user_ids': body.get('user_ids', [])}
        return {}

    async def _log_audit_entry(self, request: Request, context: AuditContext):
        try:
            user = await self._get_authenticated_user(request)

            user = user.model_dump(include={'id', 'name', 'email', 'role'}) if user else {}

            request_body = context.request_body.decode('utf-8', errors='replace')
            response_body = context.response_body.decode('utf-8', errors='replace')

            request_object = parse_and_redact_body(request_body)
            response_object = parse_and_redact_body(response_body)

            status_code = context.metadata.get('response_status_code', None)
            auth_method = self._get_auth_method(request)
            request_id = (
                request.headers.get('x-request-id')
                or request.headers.get('x-correlation-id')
                or str(uuid.uuid4())
            )
            semantic = getattr(request.state, 'audit_event', {}) or {}
            outcome = semantic.get('outcome') or self._get_outcome(status_code)
            actor = semantic.get('actor') or user
            event_type = semantic.get('event_type') or self._infer_event_type(request, status_code, user)
            target = semantic.get('target') if 'target' in semantic else self._infer_target(request, request_object)
            changes = semantic.get('changes') if 'changes' in semantic else self._infer_changes(request, request_object)
            auth_method = semantic.get('auth_method') or auth_method
            actor_type = self._get_actor_type(actor or {}, auth_method, semantic.get('actor_type'))

            entry = AuditLogEntry(
                id=request_id,
                user=user,
                audit_level=self.audit_level.value,
                verb=request.method,
                request_uri=str(request.url),
                response_status_code=status_code,
                source_ip=request.client.host if request.client else None,
                user_agent=request.headers.get('user-agent'),
                request_object=request_object,
                response_object=response_object,
                event_type=event_type,
                outcome=outcome,
                actor=actor,
                target=redact_sensitive(target or {}),
                changes=redact_sensitive(changes or {}),
                request_id=request_id,
                auth_method=auth_method,
                actor_type=actor_type,
            )

            self.audit_logger.write(entry)
        except Exception as e:
            logger.error(f'Failed to log audit entry: {str(e)}')
