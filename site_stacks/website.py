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
    aws_logs as logs,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigatewayv2,
)
from constructs import Construct
import os


class Website(Construct):
    """Construct class that will be used by the below resources classes."""

    def __init__(self, scope, construct_id, domain_name, hosted_zone_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.website_api_domain_name = None
        self.website_intake_form_lambda = None

        # Interanal variables
        self._domain_name = domain_name
        self._sub_domain_name = f"www.{self._domain_name}"
        self._api_domain_name = f"email.{self._domain_name}"
        self._hosted_zone_id = hosted_zone_id

        website_bucket, website_distribution = self._build_site()

        self.website_bucket = website_bucket
        self.website_distribution = website_distribution

    def _build_site(self):
        website_bucket = self._create_website_bucket()

        hosted_zone = self._get_hosted_zone()

        website_certificate = self._create_acm_certificate(
            "website_certificate", self._domain_name, hosted_zone
        )

        website_distribution = self._create_website_distribution(
            website_certificate, website_bucket
        )

        doamins = [self._sub_domain_name, self._domain_name]
        for doamin in doamins:
            self._create_cf_route53_record(hosted_zone, doamin, website_distribution)

        self._create_website_bucket_policy(website_bucket, website_distribution)

        intake_form_certificate = self._create_acm_certificate(
            "intake_form_certificate", self._api_domain_name, hosted_zone
        )

        self._create_intake_form_lambda()

        self._create_intake_form_api(intake_form_certificate)

        self._create_api_route53_record(hosted_zone)

        # self._deploy_website_files()

        return website_bucket, website_distribution

    def _create_website_bucket(self):
        return s3.Bucket(
            self,
            "website_bucket",
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

    def _get_hosted_zone(self):
        return route53.HostedZone.from_hosted_zone_attributes(
            self,
            "website_hosted_zone",
            hosted_zone_id=self._hosted_zone_id,
            zone_name=self._domain_name,
        )

    def _create_acm_certificate(self, construct_id, domain_name, hosted_zone):
        return acm.Certificate(
            self,
            construct_id,
            domain_name=domain_name,
            subject_alternative_names=[f"www.{domain_name}"],
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

    def _create_website_distribution(self, website_certificate, website_bucket):
        # Create OAC for cloudfront to access S3
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
        # Creating cloudfront distro
        website_distribution = cloudfront.Distribution(
            self,
            "website_distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(website_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
            ),
            domain_names=[self._domain_name, self._sub_domain_name],
            certificate=website_certificate,
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

        website_distribution.apply_removal_policy(RemovalPolicy.DESTROY)

        # Get the L1 CloudFormation resource
        cfn_website_distribution = website_distribution.node.default_child

        # Add OAC configuration
        cfn_website_distribution.add_property_override(
            "DistributionConfig.Origins.0.OriginAccessControlId",
            oac.get_att("Id"),
        )

        # Remove OAI configuration
        cfn_website_distribution.add_property_override(
            "DistributionConfig.Origins.0.S3OriginConfig.OriginAccessIdentity",
            "",
        )

        return website_distribution

    def _create_cf_route53_record(self, hosted_zone, domain_name, website_distribution):
        route53.ARecord(
            self,
            f"{domain_name}_alias_record",
            record_name=domain_name,
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(website_distribution)
            ),
        )

    def _create_api_route53_record(self, hosted_zone):
        route53.ARecord(
            self,
            "website_api_alias_record",
            record_name=self._api_domain_name,
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.ApiGatewayv2DomainProperties(
                    self.website_api_domain_name.attr_regional_domain_name,
                    self.website_api_domain_name.attr_regional_hosted_zone_id,
                )
            ),
        )

    def _create_website_bucket_policy(self, website_bucket, website_distribution):
        my_bucket_policy = iam.PolicyStatement(
            actions=["s3:GetObject"],
            effect=iam.Effect.ALLOW,
            resources=[f"{website_bucket.bucket_arn}/*"],
            principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
            conditions={
                "StringEquals": {
                    "aws:SourceArn": [
                        f"arn:aws:cloudfront::{Aws.ACCOUNT_ID}:distribution/{website_distribution.distribution_id}"
                    ]
                }
            },
        )

        website_bucket.add_to_resource_policy(my_bucket_policy)

    def _create_intake_form_lambda(self):
        self.website_intake_form_lambda = lambda_.Function(
            self,
            "website_intake_form_lambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="contact_form_intake.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            description=f"Lambda to handle intake from the contact form on {self._domain_name}.",
            environment={
                "website": self._domain_name,
                "environment": f"{os.environ.get('ENVIRONMENT')}",
            },
            log_retention=logs.RetentionDays.THREE_MONTHS,
            timeout=Duration.minutes(5),
        )

        policy_statements = [
            iam.PolicyStatement(
                actions=[
                    "ses:SendEmail",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:ses:us-east-1:{Aws.ACCOUNT_ID}:identity/{self._domain_name}",
                    f"arn:aws:ses:us-east-1:{Aws.ACCOUNT_ID}:identity/cullancarey@yahoo.com",
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "ssm:GetParameter",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:ssm:us-east-1:{Aws.ACCOUNT_ID}:parameter/{os.environ.get('ENVIRONMENT')}_google_captcha_secret"
                ],
            ),
        ]
        for policy_statement in policy_statements:
            self.website_intake_form_lambda.add_to_role_policy(policy_statement)

    def _create_intake_form_api(self, intake_form_certificate):
        website_intake_form_api = apigatewayv2.CfnApi(
            self,
            "website_intake_form_api",
            description=f"API for intake of the contact form on {self._domain_name}.",
            protocol_type="HTTP",
            route_key="POST /",
            target=self.website_intake_form_lambda.function_arn,
            name="website_intake_form_api",
        )

        self.website_api_domain_name = apigatewayv2.CfnDomainName(
            self,
            "website_api_domain_name",
            domain_name=self._api_domain_name,
            domain_name_configurations=[
                apigatewayv2.CfnDomainName.DomainNameConfigurationProperty(
                    certificate_arn=intake_form_certificate.certificate_arn,
                    endpoint_type="REGIONAL",
                    security_policy="TLS_1_2",
                )
            ],
        )

        apigatewayv2.CfnApiMapping(
            self,
            "cfn_api_mapping",
            api_id=website_intake_form_api.attr_api_id,
            domain_name=self.website_api_domain_name.domain_name,
            stage="$default",
        )

        apigatewayv2.CfnIntegration(
            self,
            "website_api_integration",
            api_id=website_intake_form_api.attr_api_id,
            integration_type="AWS_PROXY",
            connection_type="INTERNET",
            description="Integration for form intake api and form intake lambda.",
            integration_method="POST",
            integration_uri=self.website_intake_form_lambda.function_arn,
            payload_format_version="2.0",
        )

        self.website_intake_form_lambda.add_permission(
            id="website_intake_form_lambda_perms",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )
