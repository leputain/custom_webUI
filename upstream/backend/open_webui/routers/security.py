from __future__ import annotations

import importlib.metadata
import json
import logging
import platform
from pathlib import Path
from typing import Any

import aiohttp
from fastapi import APIRouter, Depends, Request
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
        from open_webui.utils.audit import set_audit_event

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


@router.get('/versions')
async def get_security_versions(request: Request, user=Depends(get_admin_or_security_curator_user)):
    if user.role == 'security_curator':
        from open_webui.utils.audit import set_audit_event

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
