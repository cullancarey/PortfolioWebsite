from aws_cdk import (
    Stack,
    aws_ssm as ssm,
)
from constructs import Construct
from my_constructs.s3_bucket import S3Bucket
from my_constructs.ssm_param_replicator import SsmParameterReplicator


class BackupWebsiteBucket(Stack):
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
        SsmParameterReplicator(
            self,
            "BackupBucketSSMReplicatorV2",
            source_region=region,
            target_region="us-east-2",
            parameters=[
                {
                    "source": bucket_arn_param.parameter_name,
                    "target": bucket_arn_param.parameter_name,
                },
                {
                    "source": bucket_domain_name_param.parameter_name,
                    "target": bucket_domain_name_param.parameter_name,
                },
                {
                    "source": bucket_name_param.parameter_name,
                    "target": bucket_name_param.parameter_name,
                },
            ],
        )
