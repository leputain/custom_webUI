# TODO

## Critical

- Decide whether deployment is internal-only, VPN-only, or internet-facing behind an access proxy.
- Confirm licensing/branding constraints based on expected user count.

## Next

- Define the first UI customization target.
- Run `npm run check` and `npm run build`.
- Rebuild and rescan the hardened Docker image after the semantic audit changes.
- Rebuild and rescan the hardened Docker image after the `security_curator` changes.
- Exercise the new audit endpoints against a real running Open WebUI instance.
- Run `npm install`, then `npm run check`, `npm run test:frontend`, and `npm run build` for the security-curator UI changes.
- Expand frontend read-only coverage across every admin settings subsection; several secret-bearing config panels intentionally remain admin-only pending redaction review.
- Add broader backend integration tests against real Open WebUI routers and DB fixtures for curator access to users, groups, analytics, and settings pages.
- Decide model backend: Ollama, OpenAI-compatible gateway, OpenRouter, or mixed.
- Decide auth strategy: local auth, OIDC, LDAP, or trusted reverse proxy headers.
- Disable signup remains the production default after first admin onboarding.
- Triage remaining low/moderate npm audit findings.
- Review upstream Dockerfile secret-like `ENV` defaults flagged by Trivy config scanning.

## Later

- Add reverse proxy template.
- Add backup and restore instructions for `/app/backend/data`.
- Add vulnerability scanning workflow for images and dependencies.
- Add a rebase procedure for new upstream releases.
- Re-check Open WebUI GitHub Security Advisories, NVD, npm audit, and Trivy before production release.
- Validate newer `pyarrow`/`torch` pins on Raspberry Pi or other constrained targets if those platforms are required.

## Technical Debt

- Deployment template currently uses image tag, not immutable image digest.
- No automated CI configured for custom branch.
