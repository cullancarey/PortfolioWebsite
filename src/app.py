#!/usr/bin/env python3
import os
from aws_cdk import App, Environment, Tags, Stack
from stacks.website_stack import Website
from stacks.acm_certificates_stack import ACMCertificates
from stacks.backup_website_bucket import BackupWebsiteBucket


def add_tags(stack: Stack, default_tags: dict):
    for k, v in default_tags.items():
        Tags.of(stack).add(k, v)
    Tags.of(stack).add("stack_name", stack.stack_name)


app = App()

cloudfront_region = "us-east-1"

environment = (
    os.environ.get("ENVIRONMENT")
    or app.node.try_get_context("environment")
    or "development"
)
environment_config = app.node.try_get_context(environment)

account_id = environment_config["account_id"]
region = environment_config["region"]
domain_name = environment_config["domain_name"]
source_file_path = environment_config["file_path"]
acm_ssm_params = environment_config["acm_ssm_params"]
backup_website_bucket_ssm_params = environment_config[
    "backup_website_bucket_ssm_params"
]

env = Environment(account=account_id, region=region)
cloudfront_env = Environment(account=account_id, region=cloudfront_region)

default_tags = {
    "environment": environment,
    "project": "personal website",
    "website": domain_name,
    "owner": "Cullan Carey",
    "created_by": "cdk",
    "managed_by": "aws-cdk",
}

certificates = ACMCertificates(
    scope=app,
    id="ACMCertificates",
    account_id=account_id,
    domain_name=domain_name,
    env_region=cloudfront_region,
    ssm_params=acm_ssm_params,
    env=cloudfront_env,
    description=f"Stack to create ACM certificates in {cloudfront_env.region} for Cloudfront",
)

backup_bucket_stack = BackupWebsiteBucket(
    scope=app,
    id="BackupWebsiteBucket",
    ssm_params=backup_website_bucket_ssm_params,
    region=region,
    env=cloudfront_env,
    description=f"Stack to deploy the website's failover bucket in {cloudfront_env.region}",
)

website_stack = Website(
    scope=app,
    id="Website",
    account_id=account_id,
    region=region,
    domain_name=domain_name,
    source_file_path=source_file_path,
    environment=environment,
    acm_ssm_params=acm_ssm_params,
    backup_website_bucket_ssm_params=backup_website_bucket_ssm_params,
    env=env,
    description="Stack to deploy the website resources",
)

website_stack.add_dependency(certificates)
website_stack.add_dependency(backup_bucket_stack)

add_tags(certificates, default_tags)
add_tags(backup_bucket_stack, default_tags)
add_tags(website_stack, default_tags)

app.synth()
