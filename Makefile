# -----------------------------
# Variables
# -----------------------------
CHECKOV_CONFIG=$(CURDIR)/.checkov.yml
TEMPLATE_DIR=cdk/cdk.out
TEMPLATES=$(wildcard $(TEMPLATE_DIR)/*.template.json)
ENV ?= development

# -----------------------------
# Python/CDK Dependencies
# -----------------------------
install-deps:
	pip install --upgrade pip
	pip install --upgrade -r cdk/requirements.txt
	pip install bandit

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
	cd cdk && npx cdk synth --context environment=$(ENV)

deploy:
	cd cdk && npx cdk deploy --all --require-approval never --context environment=$(ENV)

cdk-diff:
	cd cdk && npx cdk diff --context environment=$(ENV)

cdk-drift:
	cd cdk && npx cdk drift --context environment=$(ENV) --no-color || true

# -----------------------------
# Security Scans
# -----------------------------
checkov:
	@echo "Running Checkov on $(TEMPLATE_DIR)..."
	@for f in $(TEMPLATES); do \
		echo "Scanning $$f with Checkov"; \
		checkov --config-file $(CHECKOV_CONFIG) -f "$$f"; \
	done

cfnlint:
	@echo "Running cfn-lint on $(TEMPLATE_DIR)..."
	@for f in $(TEMPLATES); do \
		echo "Linting $$f with cfn-lint"; \
		cfn-lint "$$f"; \
	done

bandit:
	@echo "Running Bandit (Python security scanner)..."
	bandit -r -x ./cdk/cdk.out,./cdk/tests,./frontend .

# -----------------------------
# Tests & Linting
# -----------------------------
test:
	cd cdk && PYTHONPATH=. pytest tests/

lint: install-deps checkov cfnlint bandit

# -----------------------------
# Full Workflows
# -----------------------------
link: install-deps build-frontend cdk-version synth lint test

diff: install-deps build-frontend cdk-version synth cdk-diff

drift: install-deps build-frontend cdk-version synth cdk-drift