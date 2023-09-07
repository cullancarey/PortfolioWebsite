from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_s3_deployment as s3deploy,
    aws_logs as logs,
    aws_iam as iam,
    aws_certificatemanager as acm,
)
from constructs import Construct
from my_constructs.cloudfront_distribution import CloudfrontDistribution
from my_constructs.s3_bucket import S3Bucket
from my_constructs.apigw_to_lambda import ApiGwtoLambda


class Website(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        account_id: str,
        region: str,
        domain_name: str,
        source_file_path: str,
        environment: str,
        website_certificate: acm.Certificate,
        contact_form_certificate: acm.Certificate,
        backup_website_bucket: s3.Bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        _hosted_zone = route53.HostedZone.from_lookup(
            self, f"{id}-HostedZone", domain_name=domain_name
        )
        _contact_form_domain_name = f"form.{domain_name}"

        def _add_route53_record(record_name: str, cf_dist: cloudfront.Distribution):
            route53.ARecord(
                self,
                f"{record_name}-Record",
                record_name=record_name,
                zone=_hosted_zone,
                target=route53.RecordTarget.from_alias(
                    route53_targets.CloudFrontTarget(cf_dist)
                ),
            )

        website_bucket = S3Bucket(self, f"WebsiteBucket")

        website_distribution = CloudfrontDistribution(
            self,
            f"WebsiteDistribution",
            domain_name=domain_name,
            origin_type="s3",
            certificate=website_certificate,
            website_s3_bucket=website_bucket.bucket,
            backup_website_s3_bucket=backup_website_bucket,
        )

        website_bucket_policy_statement = iam.PolicyStatement(
            sid="AllowCloudFrontServicePrincipalReadOnly",
            effect=iam.Effect.ALLOW,
            principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
            actions=["s3:GetObject"],
            resources=[
                f"{website_bucket.bucket.bucket_arn}/*",
            ],
            conditions={
                "StringEquals": {
                    "AWS:SourceArn": f"arn:aws:cloudfront::{account_id}:distribution/{website_distribution.cf_distribution.distribution_id}"
                }
            },
        )

        website_bucket.bucket.add_to_resource_policy(website_bucket_policy_statement)
        # backup_website_bucket.add_to_resource_policy(website_bucket_policy_statement)

        # Add main domain
        _add_route53_record(
            record_name=domain_name, cf_dist=website_distribution.cf_distribution
        )
        # Add sub domain
        _add_route53_record(
            record_name=f"www.{domain_name}",
            cf_dist=website_distribution.cf_distribution,
        )

        apigw = ApiGwtoLambda(
            self,
            "ApiGwToLambda",
            account_id=account_id,
            region=region,
            domain_name=_contact_form_domain_name,
            environment=environment,
        )

        contact_form_distribution = CloudfrontDistribution(
            self,
            f"ContactFormDistribution",
            domain_name=_contact_form_domain_name,
            origin_type="http",
            certificate=contact_form_certificate,
            api_gateway=apigw.contact_form_api,
        )

        # Add contact form record
        _add_route53_record(
            record_name=_contact_form_domain_name,
            cf_dist=contact_form_distribution.cf_distribution,
        )

        # website_bucket.bucket.grant_read(
        #     iam.ServicePrincipal("cloudfront.amazonaws.com")
        # )

        s3deploy.BucketDeployment(
            self,
            f"{id}-WebsiteFilesDeployment",
            sources=[s3deploy.Source.asset(source_file_path)],
            destination_bucket=website_bucket.bucket,
            distribution=website_distribution.cf_distribution,
            log_retention=logs.RetentionDays.ONE_YEAR,
            retain_on_delete=False,
        )

        s3deploy.BucketDeployment(
            self,
            f"{id}-BackupWebsiteFilesDeployment",
            sources=[s3deploy.Source.asset(source_file_path)],
            destination_bucket=backup_website_bucket,
            distribution=website_distribution.cf_distribution,
            log_retention=logs.RetentionDays.ONE_YEAR,
            retain_on_delete=False,
        )
