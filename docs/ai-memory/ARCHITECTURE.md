# Architecture

## High-Level Architecture

This project is a customized fork and deployment wrapper around Open WebUI.

Source customization happens in `upstream/`, which contains the full Open WebUI application. Deployment templates live outside the upstream tree in `deploy/`.

## Main Modules

- `upstream/src/routes`: SvelteKit route pages.
- `upstream/src/lib/components`: shared Svelte UI components.
- `upstream/backend`: Python/FastAPI backend.
- `deploy/docker-compose.yml`: production-style local deployment template.
- `deploy/docker-compose.custom.yml`: override for building the local customized source.
- `notes/`: project-specific security and customization guidance.

## Data Flow

Browser users access Open WebUI through the frontend. The frontend communicates with the FastAPI backend. The backend stores application data in `/app/backend/data` and connects to LLM providers such as Ollama or OpenAI-compatible APIs.

## External Dependencies

- Open WebUI upstream repository.
- Docker image `ghcr.io/open-webui/open-webui:v0.9.6`.
- Optional Ollama or other OpenAI-compatible model endpoints.
- Optional VPN, zero-trust proxy, or authenticated reverse proxy.

## Deployment Shape

Default compose template binds the service to localhost:

```text
browser/proxy -> 127.0.0.1:3000 -> open-webui container :8080
```

For team access, place a reverse proxy or zero-trust access layer in front of the service.

For customized frontend deployments, build from `upstream/` using `deploy/docker-compose.custom.yml`.

For CVE-remediated customized deployments, use `deploy/docker-compose.hardened.yml`. It builds from the customized source image and applies OS/Python package upgrades in `deploy/Dockerfile.hardened`.

## Security Audit

Open WebUI's existing `AuditLoggingMiddleware` now writes both transport metadata and semantic security fields. Route handlers can set `request.state.audit_event` through `set_audit_event(...)` for precise event type, target, actor, and change metadata.

Admin security introspection endpoints live under:

```text
/api/v1/admin/security/audit/status
/api/v1/admin/security/versions
```

## Security Curator Role

The backend defines `security_curator` as a read-only administrative role. `get_admin_user` still permits only `admin`; read-only admin endpoints use `get_admin_or_security_curator_user`.

The frontend uses RBAC helpers in `src/lib/utils/rbac.ts`:

```text
isAdmin
isSecurityCurator
canAccessAdminPanel
isReadOnlyAdmin
```

The role is displayed as `Куратор ИБ`. UI controls for common admin mutations are hidden or disabled for this role, but backend dependencies are the authoritative control.
