from aws_cdk import (
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class S3Bucket(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create the S3 bucket
        self.bucket = s3.Bucket(
            self,
            "BucketResource",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=True,
                block_public_policy=True,
                restrict_public_buckets=True,
                ignore_public_acls=True,
            ),
        )

        # Add bucket lifecycle rule
        self.bucket.add_lifecycle_rule(
            noncurrent_version_expiration=Duration.days(2),
            enabled=True,
        )

        # Enforce TLS (HTTPS-only access)
        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="EnforceTLS",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[
                    self.bucket.bucket_arn,
                    f"{self.bucket.bucket_arn}/*",
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
            )
        )
