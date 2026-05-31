from aws_cdk import (
    Stack,
    aws_ssm as ssm,
)
from constructs import Construct
from my_constructs.s3_bucket import S3Bucket
from my_constructs.ssm_param_replicator import SSMParameterReplicator
from my_constructs.ssm_replication import build_ssm_replication_config


class BackupWebsiteBucketStack(Stack):
    def __init__(
        self, scope: Construct, id: str, ssm_params: dict, region: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Define your bucket
        self.backup_website_bucket = S3Bucket(self, "BackupWebsiteBucket")

        bucket_name = self.backup_website_bucket.bucket.bucket_name
        bucket_arn = self.backup_website_bucket.bucket.bucket_arn
        bucket_domain_name = (
            self.backup_website_bucket.bucket.bucket_regional_domain_name
        )

        # Write parameters to SSM (in the stack's region)
        bucket_arn_param = ssm.StringParameter(
            self,
            "BackupBucketArnParam",
            parameter_name=ssm_params["backup_website_bucket_arn_param"],
            string_value=bucket_arn,
        )

        bucket_domain_name_param = ssm.StringParameter(
            self,
            "BackupBucketDomainNameParam",
            parameter_name=ssm_params["backup_website_bucket_domain_name_param"],
            string_value=bucket_domain_name,
        )

        bucket_name_param = ssm.StringParameter(
            self,
            "BackupBucketNameParam",
            parameter_name=ssm_params["backup_website_bucket_name_param"],
            string_value=bucket_name,
        )

        # Replicate these parameters to another region (us-east-2)
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
            target_region="us-east-2",
            param_path_prefix=replication_config.param_path_prefix,
            parameters=replication_config.parameters,
        )
