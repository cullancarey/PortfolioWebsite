import boto3
from botocore.exceptions import ClientError

from aws_cdk import (
    Aws,
    Stack,
    aws_iam as iam,
    aws_ssm as ssm,
)
from constructs import Construct
from my_constructs.s3_bucket import S3Bucket
from my_constructs.ssm_param_replicator import SSMParameterReplicator
from my_constructs.ssm_replication import build_ssm_replication_config


class BackupWebsiteBucketStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        ssm_params: dict,
        region: str,
        replication_target_region: str = "us-east-2",
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Define your bucket
        self.backup_website_bucket = S3Bucket(self, "BackupWebsiteBucket")
        self._allow_cloudfront_read_access_to_backup_bucket()

        bucket_name = self.backup_website_bucket.bucket.bucket_name
        bucket_arn = self.backup_website_bucket.bucket.bucket_arn
        bucket_domain_name = (
            self.backup_website_bucket.bucket.bucket_regional_domain_name
        )

        # Write parameters to SSM (in the stack's region)
        # For preview environments, check if parameters already exist to avoid
        # Early Validation hook errors on re-deployment
        bucket_arn_param_name = ssm_params["backup_website_bucket_arn_param"]
        bucket_domain_param_name = ssm_params["backup_website_bucket_domain_name_param"]
        bucket_name_param_name = ssm_params["backup_website_bucket_name_param"]

        if not self._parameter_exists(bucket_arn_param_name, region):
            ssm.StringParameter(
                self,
                "BackupBucketArnParam",
                parameter_name=bucket_arn_param_name,
                string_value=bucket_arn,
            )

        if not self._parameter_exists(bucket_domain_param_name, region):
            ssm.StringParameter(
                self,
                "BackupBucketDomainNameParam",
                parameter_name=bucket_domain_param_name,
                string_value=bucket_domain_name,
            )

        if not self._parameter_exists(bucket_name_param_name, region):
            ssm.StringParameter(
                self,
                "BackupBucketNameParam",
                parameter_name=bucket_name_param_name,
                string_value=bucket_name,
            )

        # Replicate these parameters to the configured target region
        replication_config = build_ssm_replication_config(
            [
                ssm_params["backup_website_bucket_arn_param"],
                ssm_params["backup_website_bucket_domain_name_param"],
                ssm_params["backup_website_bucket_name_param"],
            ]
        )

        SSMParameterReplicator(
            self,
            "BackupBucketSSMReplicatorV2",
            source_region=region,
            target_region=replication_target_region,
            param_path_prefix=replication_config.param_path_prefix,
            parameters=replication_config.parameters,
        )

    @staticmethod
    def _parameter_exists(parameter_name: str, region: str) -> bool:
        """Check if an SSM parameter exists in the specified region.

        Args:
            parameter_name: The name of the SSM parameter
            region: The AWS region to check

        Returns:
            True if the parameter exists, False otherwise
        """
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            ssm_client.get_parameter(Name=parameter_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                return False
            # For any other error (e.g., auth), assume parameter doesn't exist
            # to allow CDK to attempt creation
            return False
        except Exception:
            # If we can't connect/check, assume it doesn't exist
            return False

    def _allow_cloudfront_read_access_to_backup_bucket(self) -> None:
        """Allow CloudFront distributions in this account to read backup objects.

        The wildcard distribution ARN is intentional: this stack deploys before
        the CloudFront distribution exists, so the specific distribution ARN is
        not yet known. Scoping to the account (distribution/*) is an accepted
        tradeoff for a single-account personal project with no other distributions
        serving from this bucket.
        """
        distribution_source_arn = (
            f"arn:{Aws.PARTITION}:cloudfront::{Aws.ACCOUNT_ID}:distribution/*"
        )

        self.backup_website_bucket.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontServicePrincipalReadOnlyBackup",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[f"{self.backup_website_bucket.bucket.bucket_arn}/*"],
                conditions={"StringLike": {"AWS:SourceArn": distribution_source_arn}},
            )
        )
