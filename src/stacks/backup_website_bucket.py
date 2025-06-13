from aws_cdk import Stack, aws_ssm as ssm
from constructs import Construct
from my_constructs.s3_bucket import S3Bucket


class BackupWebsiteBucket(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Define your bucket
        self.backup_website_bucket = S3Bucket(self, "BackupWebsiteBucket")

        # Expose bucket_name, arn, and domain_name
        bucket_name = self.backup_website_bucket.bucket.bucket_name
        bucket_arn = self.backup_website_bucket.bucket.bucket_arn
        bucket_domain_name = (
            self.backup_website_bucket.bucket.bucket_regional_domain_name
        )

        # Define website_stack_name explicitly
        website_stack_name = self.stack_name

        # Write Bucket ARN to SSM
        ssm.StringParameter(
            self,
            "BackupBucketArnParam",
            parameter_name=f"/{website_stack_name}/BackupWebsiteBucketArn",
            string_value=bucket_arn,
        )

        # Write Bucket Domain Name to SSM
        ssm.StringParameter(
            self,
            "BackupBucketDomainNameParam",
            parameter_name=f"/{website_stack_name}/BackupWebsiteBucketDomainName",
            string_value=bucket_domain_name,
        )

        # Write Bucket Name to SSM
        ssm.StringParameter(
            self,
            "BackupBucketNameParam",
            parameter_name=f"/{website_stack_name}/BackupWebsiteBucketName",
            string_value=bucket_name,
        )
