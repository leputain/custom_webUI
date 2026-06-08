# Task Log

## 2026-06-08

### Task

Localize and polish the GitHub repository presentation.

### Changed

- Rewrote the root `README.md` in Russian.
- Added a clearer project overview, status table, directory structure, quick start, custom image build steps, development commands, security guidance, and licensing/branding notes.

### Validation

- Confirmed the README describes the pinned Open WebUI `v0.9.6` source, local deployment shape, security posture, and upstream license constraints.

### Task

Prepare the project for publication to `leputain/custom_webUI`.

### Changed

- Created a temporary clone at `/tmp/custom_webUI_push.OhEYTd/repo`.
- Synchronized the local project into the clone while excluding `deploy/.env`, nested git metadata, dependency folders, caches, build outputs, virtualenvs, and local database files.
- Created commit `f060f62` with the project contents.

### Validation

- Verified the staged repository does not include `.env`, `.git`, `node_modules`, `.trivy-cache`, private-key-like files, or local database files.

### Notes

- `git push origin main` was blocked because local GitHub HTTPS credentials are not configured.

### Task

Create a local project for deploying and customizing the latest Open WebUI while accounting for critical security advisories.

### Changed

- Created `/home/zii/projects/open-webui-custom`.
- Cloned `open-webui/open-webui` at `v0.9.6` into `upstream/`.
- Created branch `custom-ui-v0.9.6`.
- Added project instructions, README, deployment template, security notes, UI customization notes, and project memory.
- Added custom compose override for building the local UI fork.

### Validation

- Verified latest tag with `git ls-remote --tags --sort=-v:refname`.
- Verified local upstream `package.json` reports version `0.9.6`.
- Verified `docker compose --env-file .env.example config` for official-image deployment.
- Verified merged custom build compose config.

### Remaining Risks

- Dependencies were not installed.
- Frontend build/checks were not run.
- At initial project creation, Docker image was not yet pulled or started.
- Custom image was not built.
- Production security posture still depends on access layer, identity provider, model backend, and enabled features.

### Next

- Confirm desired UI changes.
- Run `npm install`, `npm run check`, and `npm run build` after first UI patch.
- Re-check advisories before production.

### Task

Start the local Open WebUI deployment for browser inspection.

### Changed

- Generated a local untracked `deploy/.env` with a real `WEBUI_SECRET_KEY`.
- Pulled and started `ghcr.io/open-webui/open-webui:v0.9.6` with Docker Compose.
- Started container `open-webui-custom` bound to `127.0.0.1:3000`.

### Validation

- Verified Docker Compose reports the container as `healthy`.
- Verified `http://127.0.0.1:3000/` returns `200 OK`.
- Verified `http://127.0.0.1:3000/health` returns `{"status":true}`.
- Verified `/api/config` reports `onboarding: true` for first admin account creation.

### Notes

- First startup downloaded the default `sentence-transformers/all-MiniLM-L6-v2` embedding model into the named Docker volume and took several minutes.
- Source dependencies were not installed and the custom frontend image was not built.

### Task

Scan Open WebUI for HIGH/CRITICAL CVEs and remediate findings in the source lockfiles and deployable image.

### Changed

- Replaced vulnerable frontend `xlsx` with `npm:@e965/xlsx@0.20.3`.
- Updated frontend security-sensitive dev dependencies including `vitest` and `rollup`.
- Updated backend dependency pins in `backend/requirements*.txt` and `pyproject.toml` for vulnerable packages including `python-multipart`, `PyJWT`, `langchain-classic`, `langchain-text-splitters`, `pyarrow`, `nltk`, and `pillow`.
- Regenerated `uv.lock` and upgraded vulnerable transitive packages including `azure-core`, `gitpython`, `h11`, `httpcore`, `langsmith`, `lxml`, `mako`, `setuptools`, `torch`, `ujson`, `urllib3`, and `wsproto`.
- Enabled Node build memory headroom in the upstream Dockerfile.
- Added `deploy/Dockerfile.hardened` and `deploy/docker-compose.hardened.yml`.
- Built and started `open-webui-custom:v0.9.6-ui-hardened`.

### Validation

- `npm audit --audit-level=high`: 0 HIGH, 0 CRITICAL.
- Trivy filesystem scan for `upstream/`: 0 HIGH, 0 CRITICAL.
- Trivy image scan for `open-webui-custom:v0.9.6-ui-hardened`: 0 HIGH, 0 CRITICAL.
- Verified the running container is healthy on `127.0.0.1:3000`.
- Verified key runtime package versions inside the hardened image.

### Notes

- Reports are stored under `reports/security/`.
- Low and moderate npm audit findings remain for later triage.
- Trivy config scan previously flagged secret-like `ENV` defaults in the upstream Dockerfile. The local deployment uses `.env`; the config finding is not a CVE finding.

### Task

Implement semantic security audit logging on top of the existing Open WebUI audit middleware.

### Changed

- Extended `AuditLogEntry` with semantic fields: `event_type`, `outcome`, `actor`, `target`, `changes`, `request_id`, `auth_method`, and `actor_type`.
- Added centralized audit redaction for passwords, tokens, cookies, authorization values, API keys, and secrets.
- Added `AUDIT_LOG_RETENTION_DAYS` and wired it into Loguru audit file retention while preserving existing rotation size.
- Added `/api/v1/admin/security/audit/status`.
- Added `/api/v1/admin/security/versions` with offline-safe latest-version behavior.
- Instrumented auth, user admin, default permissions, group membership, security settings, and access grant endpoints.
- Changed authenticated non-admin access to `get_admin_user` endpoints from `401` to `403`.
- Added targeted security audit tests in `upstream/test/test_security_audit.py`.

### Validation

- `python3 -m compileall` for changed backend modules: passed.
- Dockerized targeted pytest: `10 passed`.

### Notes

- The running local container was not rebuilt after these source changes.
- `actor_type=service_account` is supported as a semantic value but Open WebUI does not currently expose a distinct service-account model; API-key requests are classified as `api_key`.

### Task

Add read-only administrative role `security_curator` and extend security audit/admin introspection.

### Changed

- Added role constants and read-only admin dependencies while preserving `get_admin_user` as admin-only.
- Allowed `security_curator` to log in as a verified app role and access selected admin GET endpoints.
- Kept user/admin mutation endpoints on real-admin dependencies, including user create/update/delete, role changes, groups mutations, model/function/pipeline mutations, webhook update, and API-key create/delete.
- Added role validation so real admins can assign `security_curator`.
- Added frontend RBAC helpers and displayed `security_curator` as `Куратор ИБ`.
- Allowed `security_curator` into the admin shell, Users, Groups, Analytics, Functions list, and Security settings.
- Hid or disabled common Users/Groups/Functions mutation controls for `security_curator`.
- Added Security settings read-only page for audit status and versions.
- Added semantic audit events for login, logout, signup, user create/update/delete, role changes, security-curator assignment/removal, groups/default permissions/config changes, access denied, and curator security views.
- Added LDAP login success/failed classification in audit inference.
- Added audit retention parser with safe default.
- Added targeted backend tests for audit semantics, redaction, retention, and security-curator read/write RBAC.

### Validation

- `python3 -m compileall` for changed backend modules: passed.
- Dockerized targeted pytest: `13 passed`.
- `npm run check`: not completed because `node_modules` is absent and `svelte-kit` is not installed.

### Notes

- The running local container was not rebuilt after these source changes.
- Secret-bearing admin config/export endpoints remain admin-only unless separately redacted and approved for curator viewing.
- Full frontend, full backend, and browser regression tests still need to run after `npm install`.
