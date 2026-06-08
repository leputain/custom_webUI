# Open WebUI Custom Project Instructions

## Purpose

This project tracks a customized Open WebUI deployment and frontend fork.

The upstream source is cloned into `upstream/` and pinned to Open WebUI `v0.9.6` on branch `custom-ui-v0.9.6`.

## Stack

- Frontend: SvelteKit, Svelte 5, Vite, Tailwind CSS.
- Backend: Python/FastAPI.
- Deployment: Docker or Docker Compose.

## Run Commands

From `upstream/`:

```bash
npm install
npm run build
npm run dev
```

Backend development from `upstream/backend/`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -U
sh dev.sh
```

Production-style local deployment:

```bash
cd deploy
docker compose --env-file .env up -d
```

## Test Commands

From `upstream/`:

```bash
npm run check
npm run test:frontend
npm run build
```

Use backend linting only after backend dependencies are installed:

```bash
npm run lint:backend
```

## Coding Conventions

- Keep changes small and reviewable.
- Prefer upstream structure and existing Svelte components.
- Do not introduce dependencies unless necessary.
- Keep customized UI changes on the `custom-ui-v0.9.6` branch.
- Document any UI change that affects branding or license posture.

## Security Rules

- Do not expose Open WebUI directly to the public internet without a VPN, zero-trust proxy, or authenticated reverse proxy.
- Pin Open WebUI releases or image digests. Do not deploy floating `main` for production.
- Keep Open WebUI branding visible unless the deployment qualifies for the documented exceptions or has an enterprise license.
- Do not store API keys, OpenAI keys, JWT secrets, database passwords, cookies, private keys, or other secrets in this repository.
- Keep `.env` untracked and use `.env.example` for placeholders.
- Re-check GitHub advisories before production deployment.

## Memory Update Rules

After meaningful work, update:

- `docs/ai-memory/TASK_LOG.md`
- `docs/ai-memory/DECISIONS.md` for durable technical decisions
- `docs/ai-memory/TODO.md` for unresolved work
- `docs/ai-memory/ARCHITECTURE.md` if deployment or frontend architecture changes

## Avoid Without Explicit Instruction

- Do not rewrite large upstream modules unnecessarily.
- Do not remove, hide, recolor, or relocate Open WebUI branding without explicit legal/product approval.
- Do not run production containers against a development data volume.
- Do not commit `.env`, local databases, uploaded files, model data, or generated secrets.
