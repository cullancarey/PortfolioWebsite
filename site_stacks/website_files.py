"""Module import for cdk packages"""
from aws_cdk import (
    aws_s3_deployment as s3deploy,
    aws_logs as logs,
)
from constructs import Construct


class WebsiteFiles(Construct):
    """Construct class that will be used by the below resources classes."""

    def __init__(
        self, scope, construct_id, website_bucket, website_distribution, **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.website_bucket = website_bucket
        self.website_distribution = website_distribution

        self._deploy_website_files()

    def _deploy_website_files(self):
        s3deploy.BucketDeployment(
            self,
            "website_files_deployment",
            sources=[s3deploy.Source.asset("src/develop")],
            destination_bucket=self.website_bucket,
            distribution=self.website_distribution,
            log_retention=logs.RetentionDays.THREE_MONTHS,
            retain_on_delete=False,
        )
