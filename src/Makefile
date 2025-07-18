CHECKOV_CONFIG=$(CURDIR)/.checkov.yml
TEMPLATE_DIR=cdk.out
TEMPLATES=$(wildcard $(TEMPLATE_DIR)/*.template.json)
ENV ?= development

.PHONY: install-deps cdk-version synth deploy checkov cfnlint lint link

install-deps:
	npm install -g aws-cdk
	pip install --upgrade -r requirements.txt

cdk-version:
	cdk --version

synth:
	cdk synth --context environment=$(ENV)

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

cdk-diff:
	@echo "Running cdk diff..."
	cdk diff --context environment=$(ENV)

test:
	PYTHONPATH=. pytest tests/

lint: checkov cfnlint

link: install-deps cdk-version synth lint test

diff: install-deps cdk-version synth cdk-diff