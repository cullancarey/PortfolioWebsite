# -----------------------------
# Variables
# -----------------------------
CHECKOV_CONFIG=$(CURDIR)/.checkov.yml
TEMPLATE_DIR=cdk/cdk.out
TEMPLATES=$(wildcard $(TEMPLATE_DIR)/*.template.json)
ENV ?= development
CDK_APP=uv run --no-sync --no-dev python app.py

.PHONY: install-deps build-frontend cdk-version synth cdk-deploy cdk-diff cdk-drift checkov cfnlint bandit test lint link diff deploy drift

# -----------------------------
# Python/CDK Dependencies
# -----------------------------
install-deps:
	cd cdk && uv sync --locked --group dev

# -----------------------------
# Frontend Build
# -----------------------------
build-frontend:
	cd frontend && npm ci && npm run build

# -----------------------------
# CDK Utilities
# -----------------------------
cdk-version:
	cd cdk && npx cdk --version

synth:
	cd cdk && npx cdk synth --app "$(CDK_APP)" --context environment=$(ENV)

cdk-deploy:
	cd cdk && npx cdk deploy --app "$(CDK_APP)" --all --require-approval never --context environment=$(ENV)

cdk-diff:
	cd cdk && npx cdk diff --app "$(CDK_APP)" --all --context environment=$(ENV)

cdk-drift:
	cd cdk && npx cdkdrift --app "$(CDK_APP)" --context environment=$(ENV) --no-color || true

# -----------------------------
# Security Scans
# -----------------------------
checkov:
	@echo "Running Checkov on $(TEMPLATE_DIR)..."
	@for f in $(TEMPLATES); do \
		echo "Scanning $$f with Checkov"; \
		(cd cdk && uv run checkov --config-file $(CHECKOV_CONFIG) -f "../$$f"); \
	done

cfnlint:
	@echo "Running cfn-lint on $(TEMPLATE_DIR)..."
	@for f in $(TEMPLATES); do \
		echo "Linting $$f with cfn-lint"; \
		(cd cdk && uv run cfn-lint "../$$f"); \
	done

bandit:
	@echo "Running Bandit (Python security scanner)..."
	cd cdk && uv run bandit -r -x ./cdk.out,./tests,../frontend assets/

# -----------------------------
# Tests & Linting
# -----------------------------
test: install-deps
	cd cdk && PYTHONPATH=. uv run --no-sync pytest tests/

lint: install-deps synth checkov cfnlint bandit

# -----------------------------
# Full Workflows
# -----------------------------
link: install-deps build-frontend cdk-version synth lint test

diff: install-deps build-frontend cdk-version synth cdk-diff

deploy: install-deps build-frontend cdk-version synth cdk-deploy

drift: install-deps build-frontend cdk-version synth cdk-drift