# Decisions

## 2026-06-08: Pin Open WebUI to v0.9.6

Decision:
Use Open WebUI `v0.9.6` as the initial source and deployment baseline.

Reason:
It is the latest verified release found on 2026-06-08 and is newer than several recent vulnerable version ranges.

Alternatives considered:
Using `main` or `dev` Docker tags.

Impact:
Production and customization work can be reviewed against a stable source snapshot. Future updates require explicit rebase/security review.

## 2026-06-08: Keep Custom Work in a Fork Branch

Decision:
Create branch `custom-ui-v0.9.6` inside `upstream/`.

Reason:
UI modifications should be tracked as patches above the upstream release.

Alternatives considered:
Editing detached HEAD or deploying only a prebuilt Docker image.

Impact:
Changes can be diffed, rebased, and reviewed more cleanly.

## 2026-06-08: Treat Deployment as Internal Infrastructure

Decision:
Default deployment template binds Open WebUI to `127.0.0.1` and assumes a proxy/VPN boundary for wider access.

Reason:
Open WebUI exposes powerful model, tool, file, and code-execution features; public exposure increases risk.

Alternatives considered:
Binding directly to all interfaces.

Impact:
Safer local default; production rollout needs a reverse proxy or access layer.

## 2026-06-08: Deploy Hardened Custom Image

Decision:
Use `open-webui-custom:v0.9.6-ui-hardened` for the local customized deployment.

Reason:
The upstream release image had HIGH/CRITICAL Trivy findings. Building a custom source image and layering OS/Python package upgrades produced a deployable image with 0 HIGH/CRITICAL findings.

Alternatives considered:
Deploying the official `ghcr.io/open-webui/open-webui:v0.9.6` image directly, or only patching lockfiles without rebuilding a runtime image.

Impact:
The deployment now uses the hardened compose override. Future upstream updates must rebuild and rescan the image before production use.

## 2026-06-08: Use Maintained xlsx Fork for CVE Remediation

Decision:
Replace `xlsx@0.18.5` with the npm alias `xlsx: npm:@e965/xlsx@0.20.3`.

Reason:
The original `xlsx` package remains vulnerable in npm audit and does not provide a fixed upstream npm release for the reported high-severity advisories.

Alternatives considered:
Keeping the original package and accepting the finding.

Impact:
Imports can continue to use `xlsx`, while npm resolves to the maintained fork. Spreadsheet-related behavior should be regression-tested during UI QA.

## 2026-06-08: Build Source Image in Slim Mode

Decision:
Set `USE_SLIM=true` in the custom Docker Compose build override.

Reason:
The non-slim build path imports model-loading dependencies during image build and failed during the local build. Slim mode avoids model preloading at build time while keeping the runtime deployment functional.

Alternatives considered:
Debugging the model preload path during build.

Impact:
Embedding/model assets may be downloaded at runtime instead of during the image build.

## 2026-06-08: Prefer CVE-Remediated Dependency Pins

Decision:
Upgrade backend and lockfile dependencies to fixed versions even where upstream had older pins.

Reason:
The user goal is to remediate all found HIGH/CRITICAL CVEs before deployment.

Alternatives considered:
Waiting for upstream Open WebUI to publish a release with these transitive dependency updates.

Impact:
The lockfile now includes newer packages such as `torch`, `pyarrow`, `urllib3`, and LangChain packages. Raspberry Pi and other constrained platforms need separate validation before use.

## 2026-06-08: Layer Semantic Audit Over Existing Middleware

Decision:
Extend `AuditLoggingMiddleware` and route-level audit annotations instead of introducing a separate audit logging subsystem.

Reason:
The requirement is to preserve existing Open WebUI audit behavior while adding security-event semantics, redaction, retention, and status/version endpoints.

Alternatives considered:
Creating a parallel security audit logger or replacing the middleware.

Impact:
Existing audit file sink, rotation, include/exclude path configuration, and audit levels remain in use. Security-sensitive routes can attach precise `target` and `changes` metadata through `request.state.audit_event`.

## 2026-06-08: Backend Is Source of Rights for Security Curator

Decision:
Add the system role `security_curator` for read-only administrative access while leaving `get_admin_user` admin-only.

Reason:
The user requirement forbids a decorative frontend-only role. Mutation endpoints must continue to depend on real admin authorization.

Alternatives considered:
Reusing the `admin` role with frontend-only disabled controls.

Impact:
GET admin endpoints that expose non-secret operational data can use `get_admin_or_security_curator_user`. POST/PUT/PATCH/DELETE endpoints and secret-bearing export/config mutation routes remain `get_admin_user`. The frontend hides or disables common mutation controls for `security_curator`, but backend 403 enforcement remains the primary control.
