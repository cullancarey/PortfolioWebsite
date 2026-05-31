# Cullan's Portfolio Website

## About

[Cullancarey.com](https://cullancarey.com) is my personal portfolio website. The app is built in React and deployed as static assets on S3 behind CloudFront.

## Repository Layout

- [frontend](frontend): Vite/React website source.
- [cdk](cdk): AWS CDK infrastructure (Python).
- [\.github/workflows](.github/workflows): CI/CD and preview workflows.

## Infrastructure Overview

Infrastructure is managed in [cdk/app.py](cdk/app.py) and split into three stacks:

- [cdk/stacks/acm_certificates_stack.py](cdk/stacks/acm_certificates_stack.py): ACM certificate creation and SSM publish/replication.
- [cdk/stacks/backup_website_bucket.py](cdk/stacks/backup_website_bucket.py): Backup bucket and SSM publish/replication.
- [cdk/stacks/website_stack.py](cdk/stacks/website_stack.py): Website bucket, CloudFront distribution, Route53 records, asset deployments.

For preview environments, [cdk/app.py](cdk/app.py) uses:

- `environment=preview`
- `preview_id` normalization
- preview-scoped stack IDs
- preview-scoped SSM paths under `/Preview/<preview_id>/...`

This isolates preview resources from development and production resources.

## Deployment Model

- `develop` branch deploys to development.
- `main` branch deploys to production.
- `feature/*` branches deploy isolated preview environments.
- Preview environments are cleaned up automatically when a PR is merged into `develop`.

See [\.github/workflows/README.md](.github/workflows/README.md) for workflow details.

## Tooling

The CDK project in [cdk](cdk) uses `uv` for Python dependency management.

Common commands:

```bash
make install-deps
make test
make lint
make diff ENV=development
make deploy ENV=development
```

The `Makefile` uses the same CDK app invocation as CI (`uv run --no-sync --no-dev python app.py`) to avoid drift between local and workflow behavior.

## Testing

- Unit and template tests: [cdk/tests](cdk/tests)
- Snapshot tests: [cdk/tests/test_snapshot.py](cdk/tests/test_snapshot.py)

If templates intentionally change, refresh snapshots with:

```bash
cd cdk && PYTHONPATH=. uv run --no-sync pytest tests/test_snapshot.py --snapshot-update
```
