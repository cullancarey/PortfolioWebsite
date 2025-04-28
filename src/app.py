#!/usr/bin/env python3
"""Module import for cdk and other required packages"""
import os
from aws_cdk import App, Environment, Tags, Stack
from stacks.website_stack import Website
from stacks.acm_certificates_stack import ACMCertificates
from stacks.backup_website_bucket import BackupWebsiteBucket


def add_tags(
    stack: Stack = None,
    app: App = None,
    default_tags: dict = None,
):
    if app:
        for k, v in default_tags.items():
            Tags.of(app).add(k, v)
    if stack:
        Tags.of(stack).add("stack_name", stack.stack_name)


app = App()

cloudfront_region = "us-east-1"

# 👇 Safe, clean way to determine environment
environment = (
    os.environ.get("ENVIRONMENT")
    or app.node.try_get_context("environment")
    or "development"
)
environment_config = app.node.try_get_context(environment)

account_id = environment_config.get("account_id")
region = environment_config.get("region")
domain_name = environment_config.get("domain_name")
source_file_path = environment_config.get("file_path")

env = Environment(account=account_id, region=region)
cloudfront_env = Environment(account=account_id, region=cloudfront_region)

# Default tags for all stacks
default_tags = {
    "environment": environment,
    "project": "personal website",
    "website": domain_name,
    "owner": "Cullan Carey",
}

add_tags(app=app, default_tags=default_tags)

certificates = ACMCertificates(
    scope=app,
    id="ACMCertificates",
    account_id=account_id,
    domain_name=domain_name,
    env=cloudfront_env,
    cross_region_references=True,
    description=f"Stack to create ACM certificates in {cloudfront_env.region} for Cloudfront",
)

backup_website_bucket = BackupWebsiteBucket(
    scope=app,
    id="BackupWebsiteBucket",
    env=cloudfront_env,
    cross_region_references=True,
    description=f"Stack to deploy the website's failover bucket in {cloudfront_env.region}",
)

Website(
    scope=app,
    id="Website",
    account_id=account_id,
    region=region,
    domain_name=domain_name,
    source_file_path=source_file_path,
    environment=environment,
    website_certificate=certificates.website_certificate.certificate,
    contact_form_certificate=certificates.contact_form_certificate.certificate,
    backup_website_bucket=backup_website_bucket.backup_website_bucket.bucket,
    env=env,
    cross_region_references=True,
    description="Stack to deploy the website resources",
)

app.synth()
