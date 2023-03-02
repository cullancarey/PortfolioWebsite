"""Module import for cdk packages"""
from aws_cdk import Stack, NestedStack
from site_stacks.website import Website
from site_stacks.website_files import WebsiteFiles


class WebsiteStack(Stack):
    """Class defining the stack to deploy the website resources"""

    def __init__(self, scope, construct_id, props, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        website = Website(
            self,
            f"{props['namespace']}-construct",
            domain_name=props["domain_name"],
            hosted_zone_id=props["hosted_zone_id"],
        )
        self.website_bucket = website.website_bucket
        self.website_distribution = website.website_distribution


class WebsiteFilesNestedStack(NestedStack):
    """Class defining the stack to deploy the website files"""

    def __init__(
        self, scope, construct_id, props, website_bucket, website_distribution, **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        WebsiteFiles(
            self,
            f"{props['namespace']}-construct",
            website_bucket=website_bucket,
            website_distribution=website_distribution,
        )
