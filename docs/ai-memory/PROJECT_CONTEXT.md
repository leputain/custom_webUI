# Project Context

## Purpose

Customized Open WebUI deployment and frontend fork for evaluating security hardening and UI modifications.

## Current Status

- Created on 2026-06-08.
- Upstream Open WebUI cloned at `v0.9.6`.
- Working branch in `upstream/`: `custom-ui-v0.9.6`.
- No dependencies installed yet.
- Official Docker image deployment was started locally on 2026-06-08.
- Local URL: `http://127.0.0.1:3000`.
- Container: `open-webui-custom`.
- Local `.env` exists with a generated `WEBUI_SECRET_KEY`; it is untracked and must not be committed.
- Source now includes a backend-enforced read-only administrative role `security_curator` displayed in the UI as `Куратор ИБ`.
- Source now includes semantic security audit logging and admin security introspection endpoints.

## Stack

- Frontend: SvelteKit, Svelte 5, Vite, Tailwind CSS.
- Backend: Python/FastAPI.
- Deployment: Docker Compose.

## Important Directories

- `upstream/`: cloned Open WebUI source.
- `deploy/`: deployment templates.
- `notes/`: security and UI customization notes.
- `docs/ai-memory/`: durable Codex project memory.

## Startup Commands

Frontend development:

```bash
cd upstream
npm install
npm run dev
```

Backend development:

```bash
cd upstream/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -U
sh dev.sh
```

Production-style compose:

```bash
cd deploy
cp .env.example .env
docker compose --env-file .env up -d
```

Stop local compose deployment:

```bash
cd deploy
docker compose --env-file .env down
```

Custom source build:

```bash
cd deploy
docker compose --env-file .env -f docker-compose.yml -f docker-compose.custom.yml build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.custom.yml up -d
```

## Validation Commands

```bash
cd upstream
npm run check
npm run test:frontend
npm run build
```

Targeted backend audit/RBAC tests:

```bash
cd upstream
docker run --rm -e WEBUI_SECRET_KEY=test-secret-key-for-audit-tests -v "$PWD:/app" -w /app --entrypoint sh open-webui-custom:v0.9.6-ui-hardened -c 'PYTHONPATH=/app/backend pytest -q /app/test/test_security_audit.py'
```

## Known Constraints

- Open WebUI `v0.6.6+` includes a branding protection clause.
- Keep Open WebUI branding visible unless a documented exception or enterprise license applies.
- Re-check advisories before production deployment.
- Do not share dev and production data volumes.

## Links

- Upstream repository: https://github.com/open-webui/open-webui
- Development docs: https://docs.openwebui.com/getting-started/advanced-topics/development/
- Hardening docs: https://docs.openwebui.com/getting-started/advanced-topics/hardening/
- License docs: https://docs.openwebui.com/license/
