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
    aws_ssm as ssm,
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
        acm_ssm_params: dict,
        backup_website_bucket_ssm_params: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        _hosted_zone = route53.HostedZone.from_lookup(
            self, f"{id}-HostedZone", domain_name=domain_name
        )
        _contact_form_domain_name = f"form.{domain_name}"

        # Load ACM cert ARNs from SSM
        website_certificate_arn = ssm.StringParameter.value_for_string_parameter(
            self, acm_ssm_params["website_cert_arn_param"]
        )
        contact_form_certificate_arn = ssm.StringParameter.value_for_string_parameter(
            self, acm_ssm_params["contact_form_cert_arn_param"]
        )

        website_certificate = acm.Certificate.from_certificate_arn(
            self, "WebsiteCertificate", website_certificate_arn
        )
        contact_form_certificate = acm.Certificate.from_certificate_arn(
            self, "ContactFormCertificate", contact_form_certificate_arn
        )

        # Load backup bucket data from SSM
        backup_bucket_arn = ssm.StringParameter.value_for_string_parameter(
            self, backup_website_bucket_ssm_params["backup_website_bucket_arn_param"]
        )
        backup_bucket_name = ssm.StringParameter.value_for_string_parameter(
            self, backup_website_bucket_ssm_params["backup_website_bucket_name_param"]
        )

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
            backup_bucket_name=backup_bucket_name,
        )

        _add_route53_record(
            record_name=domain_name, cf_dist=website_distribution.cf_distribution
        )
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

        _add_route53_record(
            record_name=_contact_form_domain_name,
            cf_dist=contact_form_distribution.cf_distribution,
        )

        website_log_group = logs.LogGroup(
            self, f"{id}-WebsiteFilesLogGroup", retention=logs.RetentionDays.ONE_YEAR
        )

        backup_log_group = logs.LogGroup(
            self,
            f"{id}-BackupWebsiteFilesLogGroup",
            retention=logs.RetentionDays.ONE_YEAR,
        )

        # Website deployment
        s3deploy.BucketDeployment(
            self,
            f"{id}-WebsiteFilesDeployment",
            sources=[s3deploy.Source.asset(source_file_path)],
            destination_bucket=website_bucket.bucket,
            distribution=website_distribution.cf_distribution,
            distribution_paths=["/*"],
            log_group=website_log_group,
            retain_on_delete=False,
        )

        # Backup deployment
        s3deploy.BucketDeployment(
            self,
            f"{id}-BackupWebsiteFilesDeployment",
            sources=[s3deploy.Source.asset(source_file_path)],
            destination_bucket=s3.Bucket.from_bucket_name(
                self, "BackupBucketDeploymentRef", backup_bucket_name
            ),
            distribution=website_distribution.cf_distribution,
            distribution_paths=["/*"],
            log_group=backup_log_group,
            retain_on_delete=False,
        )
