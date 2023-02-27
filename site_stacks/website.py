"""Module import for cdk packages"""
from aws_cdk import (
    Aws,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_iam as iam,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_ssm as ssm,
    custom_resources,
)
from constructs import Construct
from datetime import datetime


class Website(Construct):
    """Construct class that will be used by the below resources class."""

    def __init__(self, scope, construct_id, domain_name, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.backend_bucket = None
        self.backup_backend_bucket = None
        self.website_distribution = None
        self.website_certificate = None
        self.website_distribution_id_parameter = "website_distribution_id"

        self._domain_name = domain_name

    def _create_ssm_parameter(
        self, construct_id, parameter_value, param_name, description
    ):
        ssm.StringParameter(
            self,
            construct_id,
            string_value=parameter_value,
            parameter_name=param_name,
            description=description,
            simple_name=True,
        )

class WebsiteResources(Website):
    """Class that defines the resources used for cullan.click"""

    def __init__(
        self,
        scope,
        construct_id,
        hosted_zone_id,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self._hosted_zone_id = hosted_zone_id

        self._build_site()

    def _build_site(self):
        self.backup_backend_bucket = self._get_backup_backend_bucket()

        self._create_backend_bucket()

        bucket_role = self._create_backend_bucket_role()

        self._add_bucket_replication(bucket_role)

        hosted_zone = self._get_hosted_zone()

        self._create_acm_certificate(hosted_zone)

        self._create_website_distribution()

        self._create_route53_record(hosted_zone)

        self._create_backend_bucket_policy()

    def _get_backup_backend_bucket(self):
        return s3.Bucket.from_bucket_arn(
            self,
            "backup_website_bucket_arn",
            bucket_arn=f"arn:aws:s3:::backup-{self._domain_name}",
        )

    def _get_hosted_zone(self):
        return route53.HostedZone.from_hosted_zone_attributes(
            self,
            "website_hosted_zone",
            hosted_zone_id=self._hosted_zone_id,
            zone_name=self._domain_name,
        )

    def _create_backend_bucket(self):
        self.backend_bucket = s3.Bucket(
            self,
            "website_bucket",
            bucket_name=f"{self._domain_name}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    id="Delete noncurrent versions",
                    noncurrent_version_expiration=Duration.days(2),
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _create_backend_bucket_policy(self):
        my_bucket_policy = iam.PolicyStatement(
            actions=["s3:GetObject"],
            effect=iam.Effect.ALLOW,
            resources=[f"{self.backend_bucket.bucket_arn}/*"],
            principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
            conditions={
                "StringEquals": {
                    "aws:SourceArn": [
                        f"arn:aws:cloudfront::{Aws.ACCOUNT_ID}:distribution/{self.website_distribution.distribution_id}"
                    ]
                }
            },
        )

        self.backend_bucket.add_to_resource_policy(my_bucket_policy)

    def _create_backend_bucket_role(self):
        my_custom_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "s3:ListBucket",
                        "s3:GetReplicationConfiguration",
                        "s3:GetObjectVersionForReplication",
                        "s3:GetObjectVersionAcl",
                        "s3:GetObjectVersionTagging",
                        "s3:GetObjectRetention",
                        "s3:GetObjectLegalHold",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[
                        f"{self.backend_bucket.bucket_arn}",
                        f"{self.backend_bucket.bucket_arn}/*",
                        f"{self.backup_backend_bucket.bucket_arn}",
                        f"{self.backup_backend_bucket.bucket_arn}/*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "s3:ReplicateObject",
                        "s3:ReplicateDelete",
                        "s3:ReplicateTags",
                        "s3:ObjectOwnerOverrideToBucketOwner",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[
                        f"{self.backend_bucket.bucket_arn}/*",
                        f"{self.backup_backend_bucket.bucket_arn}/*",
                    ],
                ),
            ]
        )

        iam_role_policy = iam.Policy(
            self,
            "website_bucket_role_policy",
            document=my_custom_policy,
            policy_name=f"s3crr_policy_for_{self._domain_name}",
        )

        s3_iam_role = iam.Role(
            self,
            "website_bucket_role",
            assumed_by=iam.ServicePrincipal("s3.amazonaws.com"),
            description="Role for s3crr of website files.",
            role_name=f"s3crr_role_for_{self._domain_name}",
        )

        iam_role_policy.attach_to_role(s3_iam_role)

        return s3_iam_role

    def _add_bucket_replication(self, s3_iam_role):
    # Get the CloudFormation resource
        cfn_bucket = self.backend_bucket.node.default_child

        # Change its properties
        cfn_bucket.replication_configuration = {
            "role": s3_iam_role.role_arn,
            "rules": [
                {
                    "destination": {"bucket": self.backup_backend_bucket.bucket_arn},
                    "id": "Replicate to us-east-2",
                    "status": "Enabled",
                }
            ],
        }

    def _create_acm_certificate(self, hosted_zone):
        self.website_certificate = acm.Certificate(
            self,
            "website_certificate",
            domain_name=self._domain_name,
            subject_alternative_names=[f"www.{self._domain_name}"],
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

    def _create_website_distribution(self):
        oac = cloudfront.CfnOriginAccessControl(
            self,
            "MyWebsiteCfnOriginAccessControl",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name="Website Origin Access Control",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",
                # the properties below are optional
                description=f"Origin Access Control for {self._domain_name}.",
            ),
        )

        self.website_distribution = cloudfront.Distribution(
            self,
            "website_distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.OriginGroup(
                    primary_origin=origins.S3Origin(self.backend_bucket),
                    fallback_origin=origins.S3Origin(self.backup_backend_bucket),
                    fallback_status_codes=[500, 502, 503, 504],
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
            ),
            domain_names=[f"{self._domain_name}", f"www.{self._domain_name}"],
            certificate=self.website_certificate,
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            comment=f"Distribution for {self._domain_name}",
            enabled=True,
            geo_restriction=cloudfront.GeoRestriction.denylist("RU"),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=404,
                    response_page_path="/error.html",
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=403,
                    response_page_path="/error.html",
                ),
            ],
        )

        self.website_distribution.apply_removal_policy(RemovalPolicy.DESTROY)

        # Get the CloudFormation resource
        cfn_website_distribution = self.website_distribution.node.default_child

        # Adding property overrides for both origins in group
        for origin in range(2):
            # Add OAC configuration
            cfn_website_distribution.add_property_override(
                f"DistributionConfig.Origins.{origin}.OriginAccessControlId",
                oac.get_att("Id"),
            )

            # Remove OAI configuration
            cfn_website_distribution.add_property_override(
                f"DistributionConfig.Origins.{origin}.S3OriginConfig.OriginAccessIdentity",
                "",
            )

        self._create_ssm_parameter(
            "website_distribution_id_parameter",
            self.website_distribution.distribution_id,
            self.website_distribution_id_parameter,
            "Parameter holding ID of the cloudfront website distribution.",
        )

    def _create_route53_record(self, hosted_zone):
        route53.ARecord(
            self,
            "website_alias_record",
            record_name=self._domain_name,
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.website_distribution)
            ),
        )
        route53.ARecord(
            self,
            "website_sub_alias_record",
            record_name=f"www.{self._domain_name}",
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.website_distribution)
            ),
        )


class UES2WebsiteResources(Website):
    """Class that defines the resources used for cullan.click"""

    def __init__(
        self,
        scope,
        construct_id,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self._build_use2_resources()

    def _build_use2_resources(self):

        self._create_backup_backend_bucket()

        self._create_backeup_backend_bucket_policy()

    def _create_backup_backend_bucket(self):
        self.backup_backend_bucket = s3.Bucket(
            self,
            "backup_website_bucket",
            bucket_name=f"backup-{self._domain_name}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    id="Delete noncurrent versions",
                    noncurrent_version_expiration=Duration.days(2),
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _create_backeup_backend_bucket_policy(self):

        custom_resource_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["ssm:GetParameter"],
                    effect=iam.Effect.ALLOW,
                    resources=[
                        f"arn:aws:ssm:us-east-1:{Aws.ACCOUNT_ID}:parameter/{self.website_distribution_id_parameter}"
                    ],
                )
            ]
        )

        custom_resource_role_policy = iam.Policy(
            self,
            "custom_resource_role_policy",
            document=custom_resource_policy,
            policy_name="website_custom_resource_lambda_role_policy",
        )

        custom_resource_role = iam.Role(
            self,
            "website_custom_resource_role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for the lambda created by website custom resource.",
            role_name="website_custom_resource_lambda_role",
        )

        custom_resource_role_policy.attach_to_role(custom_resource_role)

        website_distribution_id = custom_resources.AwsCustomResource(
            self,
            "GetParameter",
            on_update=custom_resources.AwsSdkCall(
                action="getParameter",
                service="SSM",
                parameters={"Name": "website_distribution_id"},
                region="us-east-1",
                physical_resource_id=custom_resources.PhysicalResourceId.of(
                    str(datetime.now())
                ),
            ),
            role=custom_resource_role,
        )

        website_distribution_id_value = website_distribution_id.get_response_field(
            "Parameter.Value"
        )

        my_bucket_policy = iam.PolicyStatement(
            actions=["s3:GetObject"],
            effect=iam.Effect.ALLOW,
            resources=[f"{self.backup_backend_bucket.bucket_arn}/*"],
            principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
            conditions={
                "StringEquals": {
                    "AWS:SourceArn": [
                        f"arn:aws:cloudfront::{Aws.ACCOUNT_ID}:distribution/{website_distribution_id_value}"
                    ]
                }
            },
        )

        self.backup_backend_bucket.add_to_resource_policy(my_bucket_policy)
