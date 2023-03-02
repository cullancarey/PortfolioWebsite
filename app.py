#!/usr/bin/env python3
"""Module import for cdk and other required packages"""
import os
from aws_cdk import App, Environment, Tags
from site_stacks.website_stack import WebsiteStack, WebsiteFilesNestedStack


app = App()

print(os.environ.get("ENVIRONMENT"))


if os.environ.get("ENVIRONMENT") == "production":
    props = {
        "namespace": "website",
        "domain_name": os.environ.get("PROD_DOMAIN_NAME"),
        "hosted_zone_id": os.environ.get("PROD_HOSTED_ZONE_ID"),
    }
    env = Environment(account=os.environ.get("PROD_ACCOUNT_ID"), region="us-east-1")
    default_tags = {
        "Project": "portfolio-website",
        "Website": os.environ.get("PROD_DOMAIN_NAME"),
        "Environemnt": os.environ.get("ENVIRONMENT"),
    }
if os.environ.get("ENVIRONMENT") == "develop":
    props = {
        "namespace": "website",
        "domain_name": os.environ.get("DEV_DOMAIN_NAME"),
        "hosted_zone_id": os.environ.get("DEV_HOSTED_ZONE_ID"),
    }
    env = Environment(account=os.environ.get("DEV_ACCOUNT_ID"), region="us-east-1")
    default_tags = {
        "Project": "portfolio-website",
        "Website": os.environ.get("DEV_DOMAIN_NAME"),
        "Environemnt": os.environ.get("ENVIRONMENT"),
    }


for key, value in default_tags.items():
    Tags.of(app).add(key, value)

website_stack = WebsiteStack(
    scope=app,
    construct_id=f"{props['namespace']}-stack",
    props=props,
    env=env,
    description=f"Stack used for deploying resources for {props['domain_name']}",
)

WebsiteFilesNestedStack(
    scope=website_stack,
    construct_id=f"{props['namespace']}-files-nested-stack",
    props=props,
    website_bucket=website_stack.website_bucket,
    website_distribution=website_stack.website_distribution,
    description=f"Stack used for deploying the website files for {props['domain_name']}",
)
app.synth()
