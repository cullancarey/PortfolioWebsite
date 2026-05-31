# GitHub Actions Workflows

This directory contains deployment, diff, and preview-environment automation for the CDK stacks.

## Workflow Files

### Standard Deploy/Diff

- [deploy_env.yaml](deploy_env.yaml)
  - Trigger: push to `develop` and `main`, or manual dispatch.
  - Calls reusable [deploy.yaml](deploy.yaml) with `environment=development` or `environment=production`.

- [deploy.yaml](deploy.yaml)
  - Reusable deploy workflow (`workflow_call`).
  - Builds frontend, installs CDK deps with `uv`, synthesizes, then deploys all stacks for the target environment.

- [diff_env.yaml](diff_env.yaml)
  - Trigger: pull requests targeting `develop` or `main`.
  - Calls reusable [diff.yaml](diff.yaml) with environment chosen from base branch.

- [diff.yaml](diff.yaml)
  - Reusable diff workflow (`workflow_call`).
  - Builds frontend, installs CDK deps with `uv`, synthesizes, then diffs all stacks for the target environment.

### Preview Environments

- [preview_deploy_trigger.yaml](preview_deploy_trigger.yaml)
  - Trigger: push to `feature/*` branches.
  - Calls [preview_deploy.yaml](preview_deploy.yaml) with `preview_id` from branch name.

- [preview_deploy.yaml](preview_deploy.yaml)
  - Reusable preview deploy workflow (`workflow_call`).
  - Normalizes and validates `preview_id`.
  - Builds frontend and installs dependencies.
  - Deploys shared preview infra (`stack_scope=shared-infra`), waits for SSM replication, then deploys preview website stack (`stack_scope=website-only`).
  - Prints preview URL and attempts PR status comment (best-effort).

- [preview_cleanup_trigger.yaml](preview_cleanup_trigger.yaml)
  - Trigger: PR closed against `develop`.
  - Runs only when the PR was merged.
  - Calls [preview_cleanup.yaml](preview_cleanup.yaml) with branch-derived `preview_id`.

- [preview_cleanup.yaml](preview_cleanup.yaml)
  - Reusable preview cleanup workflow (`workflow_call`).
  - Normalizes and validates `preview_id`.
  - Builds frontend and synthesizes preview stacks.
  - Destroys website preview stack first, then shared preview infra.
  - Posts cleanup status comment to the PR.

## Permissions and Auth

These workflows use GitHub OIDC and assume an AWS deployment role via `aws-actions/configure-aws-credentials`.

Common permissions:

- `id-token: write` for OIDC token exchange.
- `contents: read` for checkout.

Preview comment steps also require:

- `issues: write`
- `pull-requests: write`

## Runtime Pattern

Across reusable workflows, the standard execution pattern is:

1. Checkout repository.
2. Set up Python, Node, and `uv`.
3. Build frontend artifacts.
4. Install CDK Python dependencies with `uv sync --locked --no-dev`.
5. Synthesize templates with explicit app command:

```bash
uv run --no-sync --no-dev python app.py
```

6. Deploy/diff/destroy stacks from the generated cloud assembly (`cdk.out`) when applicable.

This keeps CI behavior aligned with local `Makefile` usage.