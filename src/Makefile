CHECKOV_CONFIG=$(CURDIR)/.checkov.yml
TEMPLATE_DIR=cdk.out
TEMPLATES=$(wildcard $(TEMPLATE_DIR)/*.template.json)
ENV ?= development

.PHONY: install-deps cdk-version synth deploy checkov cfnlint bandit lint link diff

install-deps:
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt
	pip install bandit

cdk-version:
	npx cdk --version

synth:
	npx cdk synth --context environment=$(ENV)

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
	bandit -r -x ./cdk.out,./tests .

cdk-diff:
	@echo "Running cdk diff..."
	npx cdk diff --context environment=$(ENV)

test:
	PYTHONPATH=. pytest tests/

lint: install-deps checkov cfnlint bandit

link: install-deps cdk-version synth lint test

diff: install-deps cdk-version synth cdk-diff