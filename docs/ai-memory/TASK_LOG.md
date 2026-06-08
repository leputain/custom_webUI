# Task Log

## 2026-06-08

### Task

Block all admin settings mutation controls for `security_curator`.

### Changed

- Added a centralized read-only guard in `Settings.svelte` for `security_curator`.
- Disabled native `input`, `textarea`, `select`, and `button` controls on all non-Security Audit admin settings tabs.
- Added capture-phase blocking for click/change/input/submit/keyboard interactions before child settings components can call save/update/import/upload handlers.
- Kept the Security Audit tab exempt from the settings mutation guard so read-only audit refresh/search remains usable.
- Extended the frontend smoke test to assert the curator settings read-only guard is wired.

### Validation

- Frontend smoke test: `4 passed`.
- Filtered `svelte-check` diagnostics for `Settings.svelte` and `Settings.security.test.ts`: no diagnostics.

### Task

Complete Security Audit / Audit Log / Versions visibility for admin and `security_curator`.

### Changed

- Added read-only `GET /api/v1/admin/security/audit/logs`.
- Added safe audit log file reading from the configured `AUDIT_LOGS_FILE_PATH` only, with limit/offset, optional filters, invalid-JSON tolerance, and centralized redaction.
- Added `/audit/logs` to semantic audit always-log endpoints.
- Connected frontend `getAuditLogs`.
- Renamed the admin settings tab to `Security Audit`.
- Expanded `Settings/Security.svelte` to show Audit Status, Audit Log table, and Versions.
- Added Russian translations for the new Security Audit labels.
- Added frontend smoke test for Security Audit settings wiring.
- Expanded backend security audit tests for audit status/logs/versions RBAC, absent files, invalid JSON, redaction, path traversal resistance, and limit capping.

### Validation

- Dockerized targeted pytest: `19 passed`.
- Frontend smoke test: `3 passed`.
- Dockerized `py_compile` for changed backend modules: passed.
- Filtered `svelte-check` diagnostics for changed frontend files: no diagnostics.
- `npm run build`: passed once after the Security Audit UI change; a later repeat after adding ru-RU translations hit a native Vite/Node `Trace/breakpoint trap` during dependency transform while targeted tests and JSON validation still passed.

### Notes

- Full `npm run check` still fails on existing upstream-wide diagnostics unrelated to this change (`9655 errors and 274 warnings`).
- Running dockerized pytest against the bind-mounted workspace deletes tracked `backend/open_webui/static/*` files as a side effect; those files were restored before commit.

### Remaining Risks

- Audit log viewer reads the configured current log file; rotated compressed audit logs are not browsed.
- Frontend tests are smoke/static wiring tests because the project has no Svelte component testing harness configured.

### Task

Investigate local UI responsiveness after the customized build.

### Changed

- Added compose passthroughs for `ENABLE_OLLAMA_API` and `AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST`.
- Added those settings to `deploy/.env.example`.
- Updated the ignored local `deploy/.env` to disable Ollama API because Ollama is not running on the host.

### Validation

- Measured fast local backend responses for `/health`, `/api/config`, and `/`.
- Confirmed `host.docker.internal:11434` times out from inside the container.
- Confirmed no local service is listening on host port `11434`.

### Notes

- Logs showed `/api/models` waiting on Ollama connection errors, which can make the interface feel less responsive after login.
- The semantic audit changes are not the primary observed cause of the local UI delay.

### Task

Build and run the customized Open WebUI locally from the GitHub-synchronized repository.

### Changed

- Created ignored local `/tmp/custom_webUI_push.OhEYTd/repo/deploy/.env` with a generated `WEBUI_SECRET_KEY`.
- Rebuilt `open-webui-custom:v0.9.6-ui` from current `upstream/` source.
- Rebuilt `open-webui-custom:v0.9.6-ui-hardened` on top of the new UI image.
- Recreated and started container `open-webui-custom` on `127.0.0.1:3000`.

### Validation

- Docker build completed successfully; Svelte/Vite emitted upstream warnings but no build error.
- Container healthcheck reached `healthy`.
- `http://127.0.0.1:3000/health` returned `{"status":true}`.
- `http://127.0.0.1:3000/` returned `200 OK`.

### Notes

- The running image is `open-webui-custom:v0.9.6-ui-hardened`.
- The existing Docker named volume `deploy_open-webui-data` was preserved.

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
