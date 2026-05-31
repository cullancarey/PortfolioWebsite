from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_s3_deployment as s3deploy,
    aws_logs as logs,
    aws_certificatemanager as acm,
    aws_ssm as ssm,
)
from constructs import Construct
from my_constructs.cloudfront_distribution import CloudFrontDistribution
from my_constructs.hosted_zone import lookup_hosted_zone
from my_constructs.s3_bucket import S3Bucket

# from my_constructs.apigw_to_lambda import ApiGwtoLambda


class WebsiteStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        hosted_zone_domain_name: str,
        source_file_path: str,
        acm_ssm_params: dict,
        backup_website_bucket_ssm_params: dict,
        geo_restrictions: dict = None,
        cloudfront_price_class: str = "PRICE_CLASS_100",
        include_www_alias: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        hosted_zone = lookup_hosted_zone(
            self,
            stack_id=id,
            hosted_zone_domain_name=hosted_zone_domain_name,
        )
        website_certificate = self._load_website_certificate(acm_ssm_params)
        _backup_bucket_arn, backup_bucket_name = self._load_backup_bucket_data(
            backup_website_bucket_ssm_params
        )

        website_bucket = S3Bucket(self, "WebsiteBucket")

        website_distribution = CloudFrontDistribution(
            self,
            "WebsiteDistribution",
            domain_name=domain_name,
            certificate=website_certificate,
            website_s3_bucket=website_bucket.bucket,
            backup_bucket_name=backup_bucket_name,
            geo_restrictions=geo_restrictions,
            price_class=cloudfront_price_class,
        )

        self._create_dns_alias_records(
            hosted_zone=hosted_zone,
            domain_name=domain_name,
            distribution=website_distribution.cf_distribution,
            include_www_alias=include_www_alias,
        )

        website_log_group = self._create_log_group(name=f"{id}-WebsiteFilesLogGroup")
        backup_log_group = self._create_log_group(
            name=f"{id}-BackupWebsiteFilesLogGroupV2"
        )

        self._deploy_static_assets(
            deployment_id=f"{id}-WebsiteFilesDeployment",
            source_file_path=source_file_path,
            destination_bucket=website_bucket.bucket,
            distribution=website_distribution.cf_distribution,
            log_group=website_log_group,
        )

        self._deploy_static_assets(
            deployment_id=f"{id}-BackupWebsiteFilesDeployment",
            source_file_path=source_file_path,
            destination_bucket=s3.Bucket.from_bucket_name(
                self, "BackupBucketDeploymentRef", backup_bucket_name
            ),
            distribution=website_distribution.cf_distribution,
            log_group=backup_log_group,
        )

    def _load_website_certificate(self, acm_ssm_params: dict) -> acm.ICertificate:
        """Load the ACM certificate ARN from SSM and import it."""
        website_certificate_arn = ssm.StringParameter.value_for_string_parameter(
            self, acm_ssm_params["website_cert_arn_param"]
        )

        return acm.Certificate.from_certificate_arn(
            self, "WebsiteCertificate", website_certificate_arn
        )

    def _load_backup_bucket_data(
        self, backup_website_bucket_ssm_params: dict
    ) -> tuple[str, str]:
        """Load the backup bucket ARN and name from SSM."""
        backup_bucket_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            backup_website_bucket_ssm_params["backup_website_bucket_arn_param"],
        )
        backup_bucket_name = ssm.StringParameter.value_for_string_parameter(
            self,
            backup_website_bucket_ssm_params["backup_website_bucket_name_param"],
        )
        return backup_bucket_arn, backup_bucket_name

    def _create_dns_alias_records(
        self,
        *,
        hosted_zone: route53.IHostedZone,
        domain_name: str,
        distribution: cloudfront.Distribution,
        include_www_alias: bool,
    ) -> None:
        """Create the Route 53 alias records for the site hostname."""
        self._create_dns_alias_record(hosted_zone, domain_name, distribution)
        if include_www_alias:
            self._create_dns_alias_record(
                hosted_zone, f"www.{domain_name}", distribution
            )

    def _create_dns_alias_record(
        self,
        hosted_zone: route53.IHostedZone,
        record_name: str,
        distribution: cloudfront.Distribution,
    ) -> None:
        """Create a single Route 53 alias record to the CloudFront distribution."""
        route53.ARecord(
            self,
            f"{record_name}-Record",
            record_name=record_name,
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(
                route53_targets.CloudFrontTarget(distribution)
            ),
        )

    def _create_log_group(self, name: str) -> logs.LogGroup:
        """Create a CloudWatch log group for bucket deployment logs."""
        return logs.LogGroup(
            self,
            name,
            retention=logs.RetentionDays.ONE_YEAR,
        )

    def _deploy_static_assets(
        self,
        *,
        deployment_id: str,
        source_file_path: str,
        destination_bucket: s3.IBucket,
        distribution: cloudfront.Distribution,
        log_group: logs.LogGroup,
    ) -> None:
        """Deploy the built frontend assets to a bucket and invalidate CloudFront."""
        s3deploy.BucketDeployment(
            self,
            deployment_id,
            sources=[s3deploy.Source.asset(source_file_path)],
            destination_bucket=destination_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
            log_group=log_group,
            retain_on_delete=False,
        )
