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
from aws_cdk.aws_cloudfront_origins import S3BucketOrigin, OriginGroup
from aws_cdk.aws_cloudfront import HeadersFrameOption, HeadersReferrerPolicy
from constructs import Construct
from typing import Optional


class CloudFrontDistribution(Construct):
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
        price_class: str = "PRICE_CLASS_100",
        **kwargs,
    ) -> None:
        """Initialize the CloudFrontDistribution construct.

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
            price_class: CloudFront price class name (e.g., PRICE_CLASS_100)
            **kwargs: Additional keyword arguments passed to the parent Construct
        """
        super().__init__(scope, id, **kwargs)

        # Use default empty geo-restrictions if not provided
        if geo_restrictions is None:
            geo_restrictions = {"restriction_type": "none", "locations": []}

        # Create a shared Origin Access Control for both S3 origins.
        origin_access_control = self._build_origin_access_control(domain_name)

        self.website_cache_policy = self._build_cache_policy()
        self.response_headers_policy = self._build_response_headers_policy(domain_name)
        origin_group = self._build_origin_group(
            website_s3_bucket,
            backup_bucket_name,
            origin_access_control,
        )
        resume_redirect_function = self._build_resume_redirect_function()

        distribution_kwargs = self._build_distribution_kwargs(
            domain_name=domain_name,
            certificate=certificate,
            origin_group=origin_group,
            resume_redirect_function=resume_redirect_function,
            geo_restrictions=geo_restrictions,
            price_class=price_class,
        )

        geo_restriction = self._get_geo_restriction(geo_restrictions)
        if geo_restriction is not None:
            distribution_kwargs["geo_restriction"] = geo_restriction

        self.cf_distribution = cloudfront.Distribution(
            self,
            f"WebsiteDistribution",
            **distribution_kwargs,
        )

        self.cf_distribution.apply_removal_policy(RemovalPolicy.DESTROY)

    def _build_origin_access_control(
        self, domain_name: str
    ) -> cloudfront.S3OriginAccessControl:
        """Create the Origin Access Control used by the distribution."""
        return cloudfront.S3OriginAccessControl(
            self,
            "OriginAccessControl",
            description=f"Origin Access Control for {domain_name}.",
        )

    def _build_cache_policy(self) -> cloudfront.CachePolicy:
        """Create the cache policy for static website assets."""
        return cloudfront.CachePolicy(
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

    def _build_response_headers_policy(
        self, domain_name: str
    ) -> cloudfront.ResponseHeadersPolicy:
        """Create the response headers policy with security controls."""
        return cloudfront.ResponseHeadersPolicy(
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

    def _build_origin_group(
        self,
        website_s3_bucket: s3.IBucket,
        backup_bucket_name: str,
        origin_access_control: cloudfront.IOriginAccessControl,
    ) -> OriginGroup:
        """Build the origin group that fails over to the backup bucket."""
        return OriginGroup(
            primary_origin=S3BucketOrigin.with_origin_access_control(
                website_s3_bucket,
                origin_access_control=origin_access_control,
            ),
            fallback_origin=S3BucketOrigin.with_origin_access_control(
                s3.Bucket.from_bucket_name(
                    self, "BackupWebsiteBucketOrigin", backup_bucket_name
                ),
                origin_access_control=origin_access_control,
            ),
            fallback_status_codes=[500, 502, 503, 504],
        )

    def _build_resume_redirect_function(self) -> cloudfront.Function:
        """Create the CloudFront Function that rewrites /resume URLs."""
        return cloudfront.Function(
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

    def _build_distribution_kwargs(
        self,
        *,
        domain_name: str,
        certificate: acm.Certificate,
        origin_group: OriginGroup,
        resume_redirect_function: cloudfront.Function,
        geo_restrictions: Optional[dict],
        price_class: str,
    ) -> dict:
        """Assemble the CloudFront distribution keyword arguments."""
        distribution_kwargs = {
            "default_behavior": cloudfront.BehaviorOptions(
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
            "error_responses": [
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
            "domain_names": [domain_name, f"www.{domain_name}"],
            "default_root_object": "index.html",
            "price_class": self._resolve_price_class(price_class),
            "comment": f"Distribution for {domain_name}",
            "certificate": certificate,
            "enabled": True,
        }

        geo_restriction = self._get_geo_restriction(geo_restrictions or {})
        if geo_restriction is not None:
            distribution_kwargs["geo_restriction"] = geo_restriction

        return distribution_kwargs

    def _resolve_price_class(self, price_class: str) -> cloudfront.PriceClass:
        """Map config value to CloudFront PriceClass enum."""
        mapping = {
            "PRICE_CLASS_ALL": cloudfront.PriceClass.PRICE_CLASS_ALL,
            "PRICE_CLASS_200": cloudfront.PriceClass.PRICE_CLASS_200,
            "PRICE_CLASS_100": cloudfront.PriceClass.PRICE_CLASS_100,
        }
        try:
            return mapping[price_class]
        except KeyError as exc:
            raise ValueError(
                "price_class must be one of: "
                "PRICE_CLASS_ALL, PRICE_CLASS_200, PRICE_CLASS_100"
            ) from exc

    def _get_geo_restriction(
        self, geo_restrictions: dict
    ) -> Optional[cloudfront.GeoRestriction]:
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
        if restriction_type == "whitelist" and locations:
            return cloudfront.GeoRestriction.allowlist(*locations)

        # No geo restrictions configured means CloudFront should not receive
        # a GeoRestriction block at all.
        return None
