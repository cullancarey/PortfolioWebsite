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
        certificate: acm.Certificate,
        backup_bucket_name: str = None,
        website_s3_bucket: s3.IBucket = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        cf_oac = cloudfront.CfnOriginAccessControl(
            self,
            f"OriginAccessControl",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name="OriginAccessControl",
                origin_access_control_origin_type="s3",
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

        # CloudFront Function for /resume → /resume.pdf redirect
        resume_redirect_function = cloudfront.Function(
            self,
            "ResumeRewriteFunction",
            code=cloudfront.FunctionCode.from_inline(
                """
                function handler(event) {
                    var request = event.request;
                    var uri = request.uri;

                    // Handle /resume → rewrite
                    if (uri === "/resume" || uri === "/resume/") {
                        request.uri = "/resume.pdf";
                        return request;
                    }

                    return request;
                    }
                """
            ),
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
                function_associations=[
                    cloudfront.FunctionAssociation(
                        event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                        function=resume_redirect_function,
                    )
                ],
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
