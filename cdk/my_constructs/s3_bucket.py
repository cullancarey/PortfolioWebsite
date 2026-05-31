"""S3 bucket construct for static website hosting.

Provides a secure, versioned S3 bucket configured for:
- Server-side encryption (S3-managed)
- Public access blocking
- Versioning with configurable retention
- TLS-only access enforcement
"""

from aws_cdk import (
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class S3Bucket(Construct):
    """A secure S3 bucket construct for static website content.

    Features:
    - Server-side encryption (S3-managed)
    - Automatic versioning with noncurrent version expiration
    - Public access blocking at the bucket level
    - Deny policy for non-TLS (non-HTTPS) access

    Attributes:
        bucket (s3.Bucket): The underlying S3 bucket resource
    """

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        """Initialize the S3Bucket construct.

        Args:
            scope: The scope/parent construct
            id: The logical ID of the construct
            **kwargs: Additional keyword arguments passed to the parent Construct
        """
        super().__init__(scope, id, **kwargs)

        # Create the S3 bucket with security best practices
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

        # Add bucket lifecycle rule to manage old versions
        # Noncurrent versions are deleted after 2 days to save storage costs
        # while maintaining recent version history for rollbacks
        self.bucket.add_lifecycle_rule(
            noncurrent_version_expiration=Duration.days(2),
            enabled=True,
        )

        # Enforce TLS (HTTPS-only access) by denying all non-secure requests
        # This policy blocks any S3 operations that don't use HTTPS
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
