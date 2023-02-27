"""Module import for cdk packages"""
from aws_cdk import Stack
from site_stacks.website import WebsiteResources, UES2WebsiteResources


class WebsiteStack(Stack):
    """Class defining the stack to deploy the website resources"""

    def __init__(self, scope, construct_id, props, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        WebsiteResources(
            self,
            f"{props['namespace']}-construct",
            domain_name=props["domain_name"],
            hosted_zone_id=props["hosted_zone_id"],
        )


class WebsiteUSE2Stack(Stack):
    """Class defining the stack to deploy the website resources needed in us-east-2 region"""

    def __init__(self, scope, construct_id, props, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        UES2WebsiteResources(
            self, f"{props['namespace']}-construct", domain_name=props["domain_name"]
        )
