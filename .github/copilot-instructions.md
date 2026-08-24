# Softmobile recovery instructions for AI agents

## Repository identity — mandatory check

You are working **only** in:

`luis12duboqwe/inventario`

Product: Softmobile 2025 / Inventario de Celulares.

Recovery baseline: `main` at `c67b4b50b98983320ec3cde88f04e1c4b04ed83f`.
Primary recovery branch: `recovery/softmobile-stabilization`.

Do **not** confuse this repository with:

- `luis12duboqwe/inventario-main` — historical snapshot/backup.
- `luis12duboqwe/sistema-de-inve-sand` — different project.
- any other repository owned by the user.

If repository identity is uncertain, stop before changing files.

## Canonical recovery plan

Read `docs/RECOVERY_MASTER_PLAN.md` before any recovery change.

The code and reproducible tests are the source of truth. Historical documents that claim a phase is “100% complete” or “production ready” are not proof.

## Recovery mode

The project is in stabilization/recovery mode. Do not add unrelated new features.

Every existing area must eventually be classified as one of:

- FUNCIONA
- REPARAR
- TERMINAR
- ELIMINAR
- NO EVALUADO

Prefer repairing and consolidating existing code over creating new parallel implementations.

## Mandatory engineering rules

1. Never commit directly to `main` as part of recovery work.
2. Keep changes small, reviewable and reversible.
3. Do not add new functions to `backend/app/crud_legacy.py`.
4. Do not remove legacy code until all consumers are identified and migrated.
5. Do not introduce mocks, sample business data or fake success behavior into production routes/pages.
6. Do not add secrets, keys, databases, generated backups or runtime logs to Git.
7. Do not mix dependency upgrades with unrelated feature/refactor work.
8. Do not silently change API contracts.
9. Preserve IMEI/serial uniqueness, inventory integrity and monetary correctness as high-priority invariants.
10. Sensitive operations must preserve authorization and auditability.

## Known critical recovery findings

Treat these as open until a dedicated recovery PR verifies and resolves them:

- `frontend/package.json` and `frontend/package-lock.json` are damaged/inconsistent.
- `.github/workflows/ci.yml` contains concatenated/inconsistent CI definitions.
- `backups/.backup.key` is versioned in a public repository and must be considered compromised.
- generated backup artifacts are present in Git.
- several frontend pages contain `TODO(wire)`, placeholders or sample data.
- `crud_legacy.py` is still imported through wildcard compatibility.
- historical completion documents contradict current code.
- debug `print()` calls exist in authentication/security code.

## Before editing

For every task:

1. confirm repository and branch;
2. read the recovery plan and relevant module files;
3. locate existing tests and call sites;
4. state the concrete failure or gap;
5. avoid broad opportunistic rewrites.

## Validation requirements

A change is not complete merely because code was written.

Run the narrowest relevant checks plus the applicable global checks:

Backend:

- import/startup check;
- focused pytest tests;
- broader backend suite when contract/shared code changes.

Frontend:

- dependency install from a clean state when manifests change;
- TypeScript/typecheck;
- lint;
- Vitest tests;
- Vite build;
- Playwright/E2E for affected GOLD flows when applicable.

Always record which commands ran and whether they passed.

## GOLD business flows

Changes must not break these canonical end-to-end goals:

- GOLD-01 purchase → IMEI inventory → POS sale → payment → stock decrement → receipt/audit.
- GOLD-02 sale → return/refund/store credit → inventory/financial/audit consistency.
- GOLD-03 inter-store transfer → in transit → receiving → exact stock/IMEI movement.
- GOLD-04 cash opening → multi-method sales → counted vs theoretical → close → report/audit.
- GOLD-05 encrypted backup → clean restore → data integrity.

## Completion language

Do not claim “100% complete”, “fully finished” or “production ready” unless the release candidate satisfies the Definition of Done in `docs/RECOVERY_MASTER_PLAN.md` and the evidence is attached to the PR/release.
