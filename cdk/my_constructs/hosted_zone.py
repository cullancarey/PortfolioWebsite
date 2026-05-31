"""Shared helpers for Route53 hosted zone lookup."""

from aws_cdk import aws_route53 as route53
from constructs import Construct


def lookup_hosted_zone(
    scope: Construct,
    *,
    stack_id: str,
    hosted_zone_domain_name: str,
) -> route53.IHostedZone:
    """Look up the Route53 hosted zone for a given domain."""
    return route53.HostedZone.from_lookup(
        scope,
        f"{stack_id}-HostedZone",
        domain_name=hosted_zone_domain_name,
    )
