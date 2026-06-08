# UI Customization Scope

## Technically Easy

- Sidebar item order, labels, grouping, and visibility.
- Chat input controls, quick actions, and placeholder behavior.
- Home/workspace dashboard composition.
- Per-page density and spacing.
- Additional internal links, support contacts, and secondary notices.
- Reusable Svelte components under `upstream/src/lib/components`.

## Medium Complexity

- Custom chat workflow panels.
- Role-aware navigation.
- Custom onboarding flows.
- Model selection simplification.
- File/RAG workflow changes.
- Admin dashboard changes.

## High Complexity

- Replacing the main app shell.
- Reworking auth flows.
- Splitting frontend from backend.
- Deep design-system replacement.
- Large changes to chat streaming, tool calls, or message rendering.

## License Constraints

For Open WebUI `v0.6.6+`, keep original Open WebUI branding visible unless a documented exception applies or an enterprise license permits white-labeling.

Safe direction for this project:

- Keep Open WebUI logo/name in their default places.
- Add custom internal notices in secondary positions.
- Do not obscure or visually compete with Open WebUI identity.
- Document the fork in an About/help area if distributing beyond local internal use.
