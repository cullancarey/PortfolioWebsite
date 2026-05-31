"""CloudFront distribution construct for global content delivery.

Provides a CDN distribution with S3 origin, automatic failover to backup bucket,
custom cache/security policies, URL rewriting, and configurable geo-restrictions.
"""

from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_certificatemanager as acm,
    RemovalPolicy,
    Duration,
)
from aws_cdk.aws_cloudfront_origins import S3BucketOrigin, HttpOrigin, OriginGroup
from aws_cdk.aws_cloudfront import HeadersFrameOption, HeadersReferrerPolicy
from constructs import Construct
from typing import Optional, List


class CloudfrontDistribution(Construct):
    """CloudFront distribution for global content delivery with security.

    Creates a CloudFront distribution with the following features:
    - S3 origin with Origin Access Control (OAC) for secure access
    - Automatic failover to backup bucket on 5xx errors
    - Custom cache policy optimized for static assets (30-day default TTL)
    - Strong security headers (CSP, HSTS, X-Frame-Options, etc.)
    - CloudFront Functions for URL rewriting (e.g., /resume → /resume.pdf)
    - Configurable geographic restrictions
    - GZIP/Brotli compression enabled
    - Error page customization for 4xx/5xx responses

    Attributes:
        cf_distribution (cloudfront.Distribution): The CloudFront distribution
        website_cache_policy (cloudfront.CachePolicy): Custom cache policy
        response_headers_policy (cloudfront.ResponseHeadersPolicy): Security headers policy
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        certificate: acm.Certificate,
        backup_bucket_name: str = None,
        website_s3_bucket: s3.IBucket = None,
        geo_restrictions: Optional[dict] = None,
        **kwargs,
    ) -> None:
        """Initialize the CloudfrontDistribution construct.

        Args:
            scope: The scope/parent construct
            id: The logical ID of the construct
            domain_name: The primary domain name for the distribution
            certificate: The ACM certificate for HTTPS
            backup_bucket_name: Name of the S3 bucket for failover/origin group fallback
            website_s3_bucket: The primary S3 bucket for website content
            geo_restrictions: Optional dict with keys:
                - restriction_type: 'none', 'blacklist', or 'whitelist'
                - locations: List of ISO 3166-1 country codes (e.g., ['RU', 'KP'])
            **kwargs: Additional keyword arguments passed to the parent Construct
        """
        super().__init__(scope, id, **kwargs)

        # Use default empty geo-restrictions if not provided
        if geo_restrictions is None:
            geo_restrictions = {"restriction_type": "none", "locations": []}

        # Create Origin Access Control for secure S3 access
        # OAC is a recommended best practice over Origin Access Identity (OAI)
        # CDK doesn't natively support OAC yet, so we use L1 constructs
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

        # Custom cache policy optimized for static website assets
        # 30-day default TTL balances between freshness and cost savings
        # Brotli and Gzip compression reduce bandwidth and improve performance
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

        # Response headers policy with strong security settings
        # Includes CORS, CSP, HSTS, X-Frame-Options, and other security headers
        self.response_headers_policy = cloudfront.ResponseHeadersPolicy(
            self,
            "ResponseHeadersPolicy",
            comment=f"Response headers policy for {domain_name}",
            cors_behavior=cloudfront.ResponseHeadersCorsBehavior(
                access_control_allow_credentials=False,
                access_control_allow_headers=["*"],
                access_control_allow_methods=["GET", "HEAD", "OPTIONS"],
                access_control_allow_origins=[
                    f"https://{domain_name}",
                    f"https://www.{domain_name}",
                ],
                origin_override=True,
            ),
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                # Content Security Policy restricts content sources and helps prevent XSS
                # Includes SHA-256 hash for inline script and restricts other directives
                content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                    content_security_policy=(
                        "default-src 'self'; "
                        "script-src 'self' 'sha256-+CaFHqmuBrWElxqcKIawFMiVbQMosw0uxx0Cj5BjXKg='; "
                        "style-src 'self' 'unsafe-inline'; "
                        "img-src 'self' data:; "
                        "font-src 'self'; "
                        "frame-src 'none'; "
                        "object-src 'none'; "
                        "connect-src 'self'; "
                        "base-uri 'self'; "
                        "form-action 'none'; "
                        "upgrade-insecure-requests;"
                    ),
                    override=True,
                ),
                # X-Frame-Options: DENY prevents clickjacking attacks
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=HeadersFrameOption.DENY,
                    override=True,
                ),
                # Referrer-Policy: NO_REFERRER enhances privacy
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=HeadersReferrerPolicy.NO_REFERRER,
                    override=True,
                ),
                # HSTS: Forces HTTPS for 365 days, includes subdomains and preload
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.days(365),
                    include_subdomains=True,
                    preload=True,
                    override=True,
                ),
                # XSS Protection: Enables browser XSS protection with block mode
                xss_protection=cloudfront.ResponseHeadersXSSProtection(
                    protection=True,
                    mode_block=True,
                    override=True,
                ),
            ),
        )

        # Origin group with automatic failover to backup bucket
        # If primary bucket returns 5xx errors, CloudFront automatically routes to backup
        # This provides high availability and graceful degradation
        origin_group = OriginGroup(
            primary_origin=S3BucketOrigin(website_s3_bucket),
            fallback_origin=S3BucketOrigin(
                s3.Bucket.from_bucket_name(
                    self, "BackupWebsiteBucketOrigin", backup_bucket_name
                )
            ),
            fallback_status_codes=[500, 502, 503, 504],
        )

        # CloudFront Function for URL rewriting (viewer request event)
        # Rewrites /resume or /resume/ to /resume.pdf for clean URL handling
        # CloudFront Functions are lightweight and execute at edge locations
        resume_redirect_function = cloudfront.Function(
            self,
            "ResumeRewriteFunction",
            code=cloudfront.FunctionCode.from_inline("""
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
                """),
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
            geo_restriction=self._get_geo_restriction(geo_restrictions),
        )

        self.cf_distribution.apply_removal_policy(RemovalPolicy.DESTROY)

        # Apply OAC configuration via property overrides
        # Note: CDK doesn't natively support OAC yet, so we use L1 construct overrides
        # This is a workaround until CDK releases native L2 OAC support
        cfn_website_distribution = self.cf_distribution.node.default_child

        # Apply OAC to both origins (primary and fallback)
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

    def _get_geo_restriction(self, geo_restrictions: dict) -> cloudfront.GeoRestriction:
        """Build a CloudFront GeoRestriction based on configuration.

        Args:
            geo_restrictions: Dict with keys:
                - restriction_type: 'none', 'blacklist', or 'whitelist'
                - locations: List of ISO 3166-1 country codes

        Returns:
            cloudfront.GeoRestriction: Configured geo-restriction object
        """
        restriction_type = geo_restrictions.get("restriction_type", "none")
        locations = geo_restrictions.get("locations", [])

        if restriction_type == "blacklist" and locations:
            return cloudfront.GeoRestriction.denylist(*locations)
        elif restriction_type == "whitelist" and locations:
            return cloudfront.GeoRestriction.allowlist(*locations)
        else:
            # Default to no restrictions
            return (
                cloudfront.GeoRestriction.denylist()
            )  # Empty denylist = no restrictions
