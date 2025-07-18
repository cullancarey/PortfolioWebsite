from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_certificatemanager as acm,
    aws_apigatewayv2 as apigw,
    aws_ssm as ssm,
    RemovalPolicy,
    Aws,
    Duration,
)
from aws_cdk.aws_cloudfront_origins import S3BucketOrigin, HttpOrigin, OriginGroup
from aws_cdk.aws_cloudfront import HeadersFrameOption, HeadersReferrerPolicy
from constructs import Construct


class CloudfrontDistribution(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        origin_type: str,
        certificate: acm.Certificate,
        backup_bucket_name: str = None,
        website_s3_bucket: s3.IBucket = None,
        api_gateway: apigw.CfnApi = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        if origin_type == "s3":
            cf_oac = cloudfront.CfnOriginAccessControl(
                self,
                f"OriginAccessControl",
                origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                    name="OriginAccessControl",
                    origin_access_control_origin_type=origin_type,
                    signing_behavior="always",
                    signing_protocol="sigv4",
                    description=f"Origin Access Control for {domain_name}.",
                ),
            )

            self.website_cache_policy = cloudfront.CachePolicy(
                self,
                "WebsiteCachePolicy",
                comment="Custom cache policy for website assets",
                default_ttl=Duration.days(30),
                max_ttl=Duration.days(365),
                min_ttl=Duration.seconds(0),
                cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                header_behavior=cloudfront.CacheHeaderBehavior.none(),
                query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                enable_accept_encoding_brotli=True,
                enable_accept_encoding_gzip=True,
            )

            self.response_headers_policy = cloudfront.ResponseHeadersPolicy(
                self,
                "ResponseHeadersPolicy",
                comment=f"Response headers policy for {domain_name}",
                cors_behavior=cloudfront.ResponseHeadersCorsBehavior(
                    access_control_allow_credentials=False,
                    access_control_allow_headers=["*"],
                    access_control_allow_methods=["POST", "OPTIONS"],
                    access_control_allow_origins=["*"],
                    origin_override=True,
                ),
                security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                    content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                        content_security_policy=(
                            "default-src * data: blob:; "
                            "script-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
                            "style-src * 'unsafe-inline' data: blob:; "
                            "img-src * data: blob:; "
                            "font-src * data: blob:; "
                            "frame-src * data: blob:; "
                            "connect-src * data: blob:; "
                            "base-uri 'self'; "
                            "form-action *; "
                            "upgrade-insecure-requests;"
                        ),
                        override=True,
                    ),
                    frame_options=cloudfront.ResponseHeadersFrameOptions(
                        frame_option=HeadersFrameOption.DENY,
                        override=True,
                    ),
                    referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                        referrer_policy=HeadersReferrerPolicy.NO_REFERRER,
                        override=True,
                    ),
                    strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                        access_control_max_age=Duration.days(365),
                        include_subdomains=True,
                        preload=True,
                        override=True,
                    ),
                    xss_protection=cloudfront.ResponseHeadersXSSProtection(
                        protection=True,
                        mode_block=True,
                        override=True,
                    ),
                ),
            )

            # Using OriginGroup for primary + fallback origin handling with shared behavior
            origin_group = OriginGroup(
                primary_origin=S3BucketOrigin(website_s3_bucket),
                fallback_origin=S3BucketOrigin(
                    s3.Bucket.from_bucket_name(
                        self, "BackupWebsiteBucketOrigin", backup_bucket_name
                    )
                ),
                fallback_status_codes=[500, 502, 503, 504],
            )

            self.cf_distribution = cloudfront.Distribution(
                self,
                f"WebsiteDistribution",
                default_behavior=cloudfront.BehaviorOptions(
                    origin=origin_group,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    cache_policy=self.website_cache_policy,
                    response_headers_policy=self.response_headers_policy,
                ),
                error_responses=[
                    cloudfront.ErrorResponse(
                        http_status=403, response_page_path="/error.html"
                    ),
                    cloudfront.ErrorResponse(
                        http_status=404, response_page_path="/error.html"
                    ),
                    cloudfront.ErrorResponse(
                        http_status=500, response_page_path="/error.html"
                    ),
                    cloudfront.ErrorResponse(
                        http_status=502, response_page_path="/error.html"
                    ),
                    cloudfront.ErrorResponse(
                        http_status=503, response_page_path="/error.html"
                    ),
                    cloudfront.ErrorResponse(
                        http_status=504, response_page_path="/error.html"
                    ),
                ],
                domain_names=[domain_name, f"www.{domain_name}"],
                default_root_object="index.html",
                price_class=cloudfront.PriceClass.PRICE_CLASS_100,
                comment=f"Distribution for {domain_name}",
                certificate=certificate,
                enabled=True,
                geo_restriction=cloudfront.GeoRestriction.denylist("RU"),
            )

            self.cf_distribution.apply_removal_policy(RemovalPolicy.DESTROY)

            cfn_website_distribution = self.cf_distribution.node.default_child

            # CDK does not yet natively support OAC, so we manually apply property overrides
            cfn_website_distribution.add_property_override(
                "DistributionConfig.Origins.0.OriginAccessControlId",
                cf_oac.get_att("Id"),
            )
            cfn_website_distribution.add_property_override(
                "DistributionConfig.Origins.0.S3OriginConfig.OriginAccessIdentity",
                "",
            )
            cfn_website_distribution.add_property_override(
                "DistributionConfig.Origins.1.OriginAccessControlId",
                cf_oac.get_att("Id"),
            )
            cfn_website_distribution.add_property_override(
                "DistributionConfig.Origins.1.S3OriginConfig.OriginAccessIdentity",
                "",
            )

        if origin_type == "http":
            response_headers_policy = cloudfront.ResponseHeadersPolicy(
                self,
                f"ResponseHeadersPolicy",
                comment=f"Response headers policy for {domain_name}",
                cors_behavior=cloudfront.ResponseHeadersCorsBehavior(
                    access_control_allow_credentials=False,
                    access_control_allow_headers=["*"],
                    access_control_allow_methods=["POST", "OPTIONS"],
                    access_control_allow_origins=["*"],
                    origin_override=True,
                ),
            )

            self.cf_distribution = cloudfront.Distribution(
                self,
                f"ContactFormIntakeDistribution",
                default_behavior=cloudfront.BehaviorOptions(
                    origin=HttpOrigin(
                        domain_name=f"{api_gateway.http_api_id}.execute-api.{Aws.REGION}.amazonaws.com",
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                        http_port=80,
                        https_port=443,
                        origin_id=domain_name,
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    response_headers_policy=response_headers_policy,
                ),
                domain_names=[domain_name, f"www.{domain_name}"],
                certificate=certificate,
                comment=f"Distribution for {domain_name}",
                price_class=cloudfront.PriceClass.PRICE_CLASS_100,
                geo_restriction=cloudfront.GeoRestriction.denylist("RU"),
            )
