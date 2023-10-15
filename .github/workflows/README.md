# GitHub Actions Workflows for CDK Stack Deployment and Diff

This directory contains GitHub Actions workflows for deploying and diffing Cloud Development Kit (CDK) stacks for both development and production environments.

## Table of Contents

- [Workflows](#workflows)
  - [Deploy-CDK-Stack/Dev](#deploy-cdk-stackdev)
  - [Deploy-CDK-Stack/Prod](#deploy-cdk-stackprod)
  - [Deploy](#deploy)
  - [Diff-CDK-Stack/Dev](#diff-cdk-stackdev)
  - [Diff-CDK-Stack/Prod](#diff-cdk-stackprod)
  - [Diff](#diff)
- [Permissions](#permissions)
- [Environment Variables](#environment-variables)
- [Steps](#steps)

## Workflows

### Deploy-CDK-Stack/Dev

This workflow is triggered on a push to the `develop` branch. It deploys the CDK stack to the development environment.

### Deploy-CDK-Stack/Prod

This workflow is triggered on a push to the `main` branch. It deploys the CDK stack to the production environment.

### Deploy

This is a reusable workflow that can be called from other workflows. It takes an `environment` input to determine which environment to deploy against.

### Diff-CDK-Stack/Dev

This workflow is triggered on a pull request to the `develop` branch or manually via workflow dispatch. It performs a diff operation on the CDK stack for the development environment.

### Diff-CDK-Stack/Prod

This workflow is triggered on a pull request to the `main` branch or manually via workflow dispatch. It performs a diff operation on the CDK stack for the production environment.

### Diff

This is a reusable workflow that can be called from other workflows. It takes an `environment` input to determine which environment to diff against.

## Permissions

- `id-token: write`: Required for requesting the JWT.
- `contents: read`: Required for actions/checkout.

## Environment Variables

- `ENVIRONMENT`: The environment to deploy or diff against.
- `CDK_DEPLOY_ACCOUNT`: The AWS account ID for deployment.
- `CDK_DEPLOY_REGION`: The AWS region for deployment.

## Steps

1. **Checkout**: Checks out the repository to the GitHub Actions runner.
2. **Configure AWS Credentials**: Configures AWS credentials based on the environment.
3. **Install Dependencies**: Installs required dependencies.
4. **CDK Synth**: Synthesizes the CDK stack.
5. **Deploy/Diff Website**: Deploys or diffs the website based on the workflow.