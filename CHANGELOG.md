# Changelog

## v1.0.0 — 2026-09-10

- Documents the three portfolio flows: campaign permissions, contact interaction, and campaign-scoped reports.
- Adds architecture, environment and data-boundary documentation.
- Establishes tests for campaign isolation and role-based access.

### Running the project

Follow the environment instructions in the README, apply migrations, then run the Django development server with a local PostgreSQL instance.

### Known limitations

- This repository is a portfolio implementation; it does not include production electoral data or a hosted production tenant.
- Any public demonstration uses synthetic records only.
