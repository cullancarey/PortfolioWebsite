from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_apigatewayv2 as apigw,
    RemovalPolicy,
    Aws,
)

from constructs import Construct


class CloudfrontDistribution(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        origin_type: str,
        certificate: acm.Certificate,
        website_s3_bucket: s3.Bucket = None,
        backup_website_s3_bucket: s3.Bucket = None,
        api_gateway: apigw.CfnApi = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        if origin_type == "s3":
            # Create OAC for cloudfront to access S3
            cf_oac = cloudfront.CfnOriginAccessControl(
                self,
                f"OriginAccessControl",
                origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                    name=f"OriginAccessControl",
                    origin_access_control_origin_type=origin_type,
                    signing_behavior="always",
                    signing_protocol="sigv4",
                    # the properties below are optional
                    description=f"Origin Access Control for {domain_name}.",
                ),
            )

            self.cf_distribution = cloudfront.Distribution(
                self,
                f"WebsiteDistribution",
                default_behavior=cloudfront.BehaviorOptions(
                    origin=origins.OriginGroup(
                        primary_origin=origins.S3Origin(bucket=website_s3_bucket),
                        fallback_origin=origins.S3Origin(
                            bucket=backup_website_s3_bucket
                        ),
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    response_headers_policy=cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
                ),
                error_responses=[
                    cloudfront.ErrorResponse(
                        http_status=404,
                        response_page_path="/error.html",
                    ),
                    cloudfront.ErrorResponse(
                        http_status=403,
                        response_page_path="/error.html",
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

            # Get the L1 CloudFormation resource
            cfn_website_distribution = self.cf_distribution.node.default_child

            # Add OAC configuration
            cfn_website_distribution.add_property_override(
                "DistributionConfig.Origins.0.OriginAccessControlId",
                cf_oac.get_att("Id"),
            )

            # Remove OAI configuration
            cfn_website_distribution.add_property_override(
                "DistributionConfig.Origins.0.S3OriginConfig.OriginAccessIdentity",
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

            # CloudFront Distribution for API Gateway
            self.cf_distribution = cloudfront.Distribution(
                self,
                f"ContactFormIntakeDistribution",
                default_behavior=cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        domain_name=f"{api_gateway.attr_api_id}.execute-api.{Aws.REGION}.amazonaws.com",
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
