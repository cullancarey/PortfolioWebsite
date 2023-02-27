#!/usr/bin/env python3

import os
from aws_cdk import App, Environment
from site_stacks.website_stack import WebsiteStack, WebsiteUSE2Stack


app = App()
props = {
    "namespace": "website",
    "USE2-namespace": "USE2-website",
    "domain_name": app.node.try_get_context("domain_name"),
    "hosted_zone_id": app.node.try_get_context("hosted_zone_id")
}

WebsiteStack(
    scope=app,
    construct_id=f"{props['namespace']}-stack",
    props=props,
    env=virginia_env,
    description=f"Stack used for deploying resources for {props['domain_name']}",
)

WebsiteUSE2Stack(
    scope=app,
    construct_id=f"{props['USE2-namespace']}-stack",
    props=props,
    env=ohio_env,
    description=f"Backup backend S3 bucket used for {props['domain_name']}",
)
app.synth()
