from __future__ import annotations

import importlib.metadata
import json
import logging
import platform
from pathlib import Path
from typing import Any

import aiohttp
from fastapi import APIRouter, Depends, Query, Request
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AUDIT_EXCLUDED_PATHS,
    AUDIT_INCLUDED_PATHS,
    AUDIT_LOG_FILE_ROTATION_SIZE,
    AUDIT_LOG_LEVEL,
    AUDIT_LOG_RETENTION_DAYS,
    AUDIT_LOGS_FILE_PATH,
    ENABLE_AUDIT_GET_REQUESTS,
    ENABLE_AUDIT_LOGS_FILE,
    ENABLE_AUDIT_STDOUT,
    ENABLE_VERSION_UPDATE_CHECK,
    OFFLINE_MODE,
    MAX_BODY_LOG_SIZE,
    VERSION,
)
from open_webui.utils.auth import get_admin_or_security_curator_user
from open_webui.utils.audit import redact_sensitive, set_audit_event

log = logging.getLogger(__name__)

router = APIRouter()

CRITICAL_DEPENDENCIES = [
    'open-webui',
    'fastapi',
    'starlette',
    'uvicorn',
    'pydantic',
    'sqlalchemy',
    'pyjwt',
    'python-multipart',
    'langchain',
    'langchain-classic',
    'langchain-text-splitters',
    'httpx',
    'aiohttp',
    'h11',
    'httpcore',
    'urllib3',
    'pillow',
    'pyarrow',
    'nltk',
    'torch',
]


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _frontend_package_version() -> str | None:
    package_json = Path(__file__).resolve().parents[3] / 'package.json'
    try:
        return json.loads(package_json.read_text()).get('version')
    except Exception:
        return None


def _safe_audit_log_path() -> Path:
    return Path(AUDIT_LOGS_FILE_PATH).expanduser().resolve()


def _matches_filter(
    item: dict[str, Any], *, event_type: str | None, outcome: str | None, user_id: str | None, search: str | None
) -> bool:
    if event_type and str(item.get('event_type', '')).lower() != event_type.lower():
        return False
    if outcome and str(item.get('outcome', '')).lower() != outcome.lower():
        return False
    if user_id:
        actor = item.get('actor') if isinstance(item.get('actor'), dict) else {}
        user = item.get('user') if isinstance(item.get('user'), dict) else {}
        if user_id not in {str(actor.get('id', '')), str(user.get('id', ''))}:
            return False
    if search:
        needle = search.lower()
        haystack = json.dumps(item, ensure_ascii=False, default=str).lower()
        if needle not in haystack:
            return False
    return True


def _read_audit_log_items(
    *,
    limit: int,
    offset: int,
    event_type: str | None = None,
    outcome: str | None = None,
    user_id: str | None = None,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    path = _safe_audit_log_path()
    if not path.is_file():
        return [], False

    items: list[dict[str, Any]] = []
    skipped = 0
    with path.open('r', encoding='utf-8', errors='replace') as audit_file:
        for line in reversed(audit_file.readlines()):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(item, dict):
                continue

            item = redact_sensitive(item)
            if not _matches_filter(item, event_type=event_type, outcome=outcome, user_id=user_id, search=search):
                continue

            if skipped < offset:
                skipped += 1
                continue

            items.append(item)
            if len(items) >= limit:
                break

    return items, True


async def _latest_open_webui_version() -> str | None:
    if not ENABLE_VERSION_UPDATE_CHECK or OFFLINE_MODE:
        return None

    try:
        timeout = aiohttp.ClientTimeout(total=1)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                'https://api.github.com/repos/open-webui/open-webui/releases/latest',
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return str(data.get('tag_name', '')).lstrip('v') or None
    except Exception as exc:
        log.debug(f'Failed to fetch latest Open WebUI version: {exc}')
        return None


async def _ollama_versions(request: Request) -> list[dict[str, Any]]:
    config = request.app.state.config
    if not getattr(config, 'ENABLE_OLLAMA_API', False):
        return []

    versions = []
    timeout = aiohttp.ClientTimeout(total=1)
    for idx, base_url in enumerate(getattr(config, 'OLLAMA_BASE_URLS', []) or []):
        api_config = getattr(config, 'OLLAMA_API_CONFIGS', {}).get(
            str(idx),
            getattr(config, 'OLLAMA_API_CONFIGS', {}).get(base_url, {}),
        )
        if not api_config.get('enable', True):
            continue

        headers = {}
        if api_config.get('key'):
            headers['Authorization'] = 'Bearer ' + api_config['key']

        item = {'url_idx': idx, 'version': None, 'available': False}
        try:
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                async with session.get(
                    f'{base_url}/api/version',
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    item['version'] = data.get('version')
                    item['available'] = True
        except Exception as exc:
            item['error'] = str(exc)
        versions.append(item)

    return versions


@router.get('/audit/status')
async def get_audit_status(request: Request, user=Depends(get_admin_or_security_curator_user)):
    if user.role == 'security_curator':
        set_audit_event(
            request,
            'security_curator.audit.viewed',
            outcome='success',
            actor=user.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'type': 'audit_status'},
        )
    return {
        'enabled': AUDIT_LOG_LEVEL != 'NONE' and (ENABLE_AUDIT_LOGS_FILE or ENABLE_AUDIT_STDOUT),
        'audit_level': AUDIT_LOG_LEVEL,
        'file_enabled': ENABLE_AUDIT_LOGS_FILE,
        'file_path': AUDIT_LOGS_FILE_PATH,
        'rotation_size': AUDIT_LOG_FILE_ROTATION_SIZE,
        'retention_days': AUDIT_LOG_RETENTION_DAYS,
        'stdout_enabled': ENABLE_AUDIT_STDOUT,
        'included_paths': AUDIT_INCLUDED_PATHS,
        'excluded_paths': AUDIT_EXCLUDED_PATHS,
        'get_requests_enabled': ENABLE_AUDIT_GET_REQUESTS,
        'max_body_log_size': MAX_BODY_LOG_SIZE,
    }


@router.get('/audit/logs')
async def get_audit_logs(
    request: Request,
    user=Depends(get_admin_or_security_curator_user),
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
    limit = min(limit, 1000)
    set_audit_event(
        request,
        'security.audit_log.viewed',
        outcome='success',
        actor=user.model_dump(include={'id', 'name', 'email', 'role'}),
        target={'type': 'audit_log'},
    )

    items, file_exists = _read_audit_log_items(
        limit=limit,
        offset=offset,
        event_type=event_type,
        outcome=outcome,
        user_id=user_id,
        search=search,
    )

    response = {
        'items': items,
        'limit': limit,
        'offset': offset,
        'total_returned': len(items),
        'file_exists': file_exists,
    }
    if not file_exists:
        response['message'] = 'Audit log file does not exist yet'
    return response


@router.get('/versions')
async def get_security_versions(request: Request, user=Depends(get_admin_or_security_curator_user)):
    if user.role == 'security_curator':
        set_audit_event(
            request,
            'security_curator.versions.viewed',
            outcome='success',
            actor=user.model_dump(include={'id', 'name', 'email', 'role'}),
            target={'type': 'security_versions'},
        )
    dependency_versions = {
        package_name: version
        for package_name in CRITICAL_DEPENDENCIES
        if (version := _package_version(package_name)) is not None
    }
    openai_compatible = [
        {'url_idx': idx, 'configured': True}
        for idx, _ in enumerate(getattr(request.app.state.config, 'OPENAI_API_BASE_URLS', []) or [])
    ]

    return {
        'open_webui_version': VERSION,
        'backend_version': _package_version('open-webui') or VERSION,
        'python_version': platform.python_version(),
        'frontend_package_version': _frontend_package_version() or VERSION,
        'critical_dependencies': dependency_versions,
        'providers': {
            'ollama': await _ollama_versions(request),
            'openai_compatible': openai_compatible,
        },
        'update_check_enabled': ENABLE_VERSION_UPDATE_CHECK,
        'offline_mode': OFFLINE_MODE,
        'latest_available_version': await _latest_open_webui_version(),
    }
