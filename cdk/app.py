#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path
from aws_cdk import App, Environment, Tags, Stack
from stacks.website_stack import WebsiteStack
from stacks.acm_certificates_stack import ACMCertificatesStack
from stacks.backup_website_bucket import BackupWebsiteBucketStack
from config import EnvironmentConfig


def add_tags(stack: Stack, default_tags: dict):
    for k, v in default_tags.items():
        Tags.of(stack).add(k, v)
    Tags.of(stack).add("stack_name", stack.stack_name)


def normalize_preview_id(value: str) -> str:
    """Normalize a preview identifier for use in DNS labels and stack IDs."""
    normalized = re.sub(r"[^a-z0-9-]", "-", value.lower()).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    if not normalized:
        raise ValueError("preview_id must contain at least one letter or number")
    return normalized[:40].rstrip("-")


def preview_stack_suffix(preview_id: str) -> str:
    """Convert a preview ID into a compact PascalCase stack suffix."""
    parts = [part for part in preview_id.split("-") if part]
    return "".join(part.capitalize() for part in parts)


def load_environment_context(environment: str) -> dict:
    """Load stable environment configuration from version-controlled JSON."""
    config_path = Path(__file__).with_name("environments.json")
    with config_path.open("r", encoding="utf-8") as file:
        all_config = json.load(file)

    defaults = all_config.get("defaults", {})
    if not isinstance(defaults, dict):
        raise TypeError("defaults must be a JSON object")

    env_config = all_config.get(environment)
    if env_config is None:
        raise ValueError(
            f"No configuration found for environment '{environment}'. "
            f"Check that it exists in {config_path.name}."
        )
    if not isinstance(env_config, dict):
        raise TypeError(f"Environment '{environment}' must map to a JSON object")

    return {**defaults, **env_config}


app = App()

environment = os.environ.get("ENVIRONMENT") or app.node.try_get_context("environment")
if not environment:
    raise ValueError(
        "Deployment environment is required. Set ENVIRONMENT or pass "
        "--context environment=<environment>."
    )

stack_scope = app.node.try_get_context("stack_scope") or "full"
valid_stack_scopes = {"full", "shared-infra", "website-only"}
if stack_scope not in valid_stack_scopes:
    raise ValueError("stack_scope must be one of: full, shared-infra, website-only")

preview_id_value = app.node.try_get_context("preview_id")
preview_id = normalize_preview_id(str(preview_id_value)) if preview_id_value else None
if preview_id and environment != "preview":
    raise ValueError("preview_id is only supported with environment=preview")

environment_config = EnvironmentConfig.from_context(
    load_environment_context(environment)
)

account_id = environment_config.account_id
region = environment_config.region
domain_name = environment_config.domain_name
hosted_zone_domain_name = environment_config.hosted_zone_domain_name
source_file_path = environment_config.file_path
cloudfront_region = environment_config.cloudfront_region
replication_target_region = environment_config.replication_target_region
cloudfront_price_class = environment_config.cloudfront_price_class
acm_ssm_params = environment_config.acm_ssm_params
backup_website_bucket_ssm_params = environment_config.backup_website_bucket_ssm_params
geo_restrictions = environment_config.geo_restrictions.to_dict()
include_www_alias = True

if preview_id:
    domain_name = f"{preview_id}.{domain_name}"
    include_www_alias = False

env = Environment(account=account_id, region=region)
cloudfront_env = Environment(account=account_id, region=cloudfront_region)

default_tags = {
    "environment": environment,
    "project": "personal website",
    "website": domain_name,
    "owner": "Cullan Carey",
    "created_by": "cdk",
    "managed_by": "aws-cdk",
    "github": "https://github.com/cullancarey/PortfolioWebsite",
}
if preview_id:
    default_tags["preview_id"] = preview_id

certificates = None
backup_bucket_stack = None

if stack_scope in {"full", "shared-infra"}:
    certificates = ACMCertificatesStack(
        scope=app,
        id="ACMCertificates",
        domain_name=domain_name,
        hosted_zone_domain_name=hosted_zone_domain_name,
        env_region=cloudfront_region,
        replication_target_region=replication_target_region,
        ssm_params=acm_ssm_params,
        environment=environment,
        env=cloudfront_env,
        description=f"Stack to create ACM certificates in {cloudfront_env.region} for Cloudfront",
    )

    backup_bucket_stack = BackupWebsiteBucketStack(
        scope=app,
        id="BackupWebsiteBucket",
        ssm_params=backup_website_bucket_ssm_params,
        region=cloudfront_region,
        replication_target_region=replication_target_region,
        env=cloudfront_env,
        description=f"Stack to deploy the website's failover bucket in {cloudfront_env.region}",
    )

    add_tags(certificates, default_tags)
    add_tags(backup_bucket_stack, default_tags)

if stack_scope in {"full", "website-only"}:
    website_stack_id = "Website"
    if preview_id:
        website_stack_id = f"WebsitePreview{preview_stack_suffix(preview_id)}"

    website_stack = WebsiteStack(
        scope=app,
        id=website_stack_id,
        domain_name=domain_name,
        hosted_zone_domain_name=hosted_zone_domain_name,
        source_file_path=source_file_path,
        acm_ssm_params=acm_ssm_params,
        backup_website_bucket_ssm_params=backup_website_bucket_ssm_params,
        geo_restrictions=geo_restrictions,
        cloudfront_price_class=cloudfront_price_class,
        include_www_alias=include_www_alias,
        env=env,
        description="Stack to deploy the website resources",
    )

    if certificates is not None and backup_bucket_stack is not None:
        website_stack.add_dependency(certificates)
        website_stack.add_dependency(backup_bucket_stack)

    add_tags(website_stack, default_tags)

app.synth()
