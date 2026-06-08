# Security Review Notes

Review date: 2026-06-08

## Baseline

Open WebUI `v0.9.6` is the current pinned baseline for this project.

## Relevant Recent Issues

Known recent Open WebUI vulnerability classes include:

- Stored XSS in rendered UI content and previews.
- SSRF, including redirect-based SSRF.
- Tool authorization bypasses.
- Direct connection/code injection.
- Privilege escalation from administrator-controlled content.
- Cross-instance cache poisoning where shared Redis/cache names are not isolated.

Examples to track before production:

- `CVE-2026-45665`: stored XSS in the Banner component prior to `0.8.0`; fixed in `0.8.0`.
- `CVE-2025-64496`: Direct Connections code injection issue reported fixed in `0.6.35`.
- `GHSL-2026-002`: chat completion API tool restriction bypass reported against `0.6.43`.

## Mitigation Plan

1. Deploy only a pinned release or image digest.
2. Run behind VPN, zero-trust proxy, or authenticated reverse proxy.
3. Keep the container bound to `127.0.0.1` unless a proxy is configured.
4. Keep signup disabled after bootstrap; default new users to `pending`.
5. Use SSO/OIDC for teams where possible.
6. Keep API passthrough disabled unless explicitly required.
7. Restrict API key endpoints.
8. Keep code execution/interpreter on `pyodide`; avoid Jupyter for untrusted users.
9. Set restrictive `IFRAME_CSP`.
10. Separate dev and production data volumes.
11. Re-check GitHub Security Advisories and NVD before production deployment.
12. Re-run frontend build/checks after UI changes.

## Open Questions

- Expected user count and license/branding path.
- Public internet exposure or internal-only deployment.
- Identity provider: local auth, LDAP, OIDC, or zero-trust proxy.
- Model backend: Ollama, OpenAI-compatible API, OpenRouter, local gateway, or mixed.
- Whether tools/functions/pipelines/terminal are required.
