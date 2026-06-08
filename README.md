# Open WebUI Custom

Local project for evaluating, hardening, deploying, and customizing the Open WebUI frontend.

## Current Baseline

- Upstream: https://github.com/open-webui/open-webui
- Pinned release: `v0.9.6`
- Commit: `1a97751e376e00a1897bc3679215ae1c7bd8fd42`
- Local source: `upstream/`
- Working branch: `custom-ui-v0.9.6`

The project is intentionally pinned to a release tag. Production deployments should not use a floating `main` tag without a separate update and security review.

## Security Position

Open WebUI can be deployed, but treat it as sensitive internal infrastructure:

- Put it behind VPN, zero-trust access, or an authenticated reverse proxy.
- Pin the image or source version.
- Disable open signup after creating the first admin.
- Keep new users in `pending` by default.
- Use strong `WEBUI_SECRET_KEY`.
- Prefer SSO/OIDC for team deployments.
- Restrict API keys and passthrough endpoints.
- Be careful with tools, functions, pipelines, Jupyter, terminal, and model-controlled code execution.
- Keep `IFRAME_CSP` restrictive because artifacts and previews can render model/user-provided HTML.

Known recent vulnerability themes:

- Stored XSS and HTML preview issues.
- SSRF and redirect-based SSRF.
- Tool authorization bypasses.
- Direct connection/code injection issues.
- Privilege escalation from admin-level actions to super admin.

Latest `v0.9.6` is newer than the versions referenced by several recent advisories, but a fresh advisory check is still required before production deployment.

## Customization Scope

Allowed and practical without touching backend:

- Change chat page layout and density.
- Add internal workflow buttons or panels.
- Add custom landing/home workspace elements.
- Add secondary organization notices, help links, and support contacts.
- Adjust non-brand visual styling while keeping Open WebUI identity intact.
- Add or modify Svelte components under `upstream/src/lib/components`.
- Change routes under `upstream/src/routes`.

Constrained by the Open WebUI license for `v0.6.6+`:

- Open WebUI branding must stay visible unless deployment has 50 or fewer users in a 30-day period, written permission, or an enterprise license.
- Do not remove, obscure, shrink, recolor, replace, or relocate Open WebUI branding without confirming the license path.
- Do not present the fork as official Open WebUI.

Deep customization is technically possible because the frontend source is available, but it increases rebase cost when upstream releases security fixes.

## Local Development

Frontend from source:

```bash
cd upstream
npm install
npm run build
npm run dev
```

Backend from source:

```bash
cd upstream/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -U
sh dev.sh
```

Official docs expect frontend at `http://localhost:5173` and backend at `http://localhost:8080`.

## Production-Style Deployment

Use `deploy/docker-compose.yml` as a starting point:

```bash
cd deploy
cp .env.example .env
docker compose --env-file .env up -d
```

Fill `.env` with local secrets before starting. Do not commit `.env`.

After custom frontend changes, build the local image instead of the official image:

```bash
cd deploy
docker compose --env-file .env -f docker-compose.yml -f docker-compose.custom.yml build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.custom.yml up -d
```

## Next UI Work

Start with a narrow UI target:

1. Chat workspace layout.
2. Login/home experience.
3. Sidebar/navigation.
4. Admin/user settings.
5. Branding-compliant internal notices.

Each UI change should be followed by `npm run check` and `npm run build`.
