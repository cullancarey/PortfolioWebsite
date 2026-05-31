from aws_cdk import Stack, aws_ssm as ssm
from constructs import Construct
from my_constructs.acm_certificate import AcmCertificate
from my_constructs.hosted_zone import lookup_hosted_zone
from my_constructs.ssm_param_replicator import SSMParameterReplicator
from my_constructs.ssm_replication import build_ssm_replication_config


class ACMCertificatesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        hosted_zone_domain_name: str,
        env_region: str,
        ssm_params: dict,
        replication_target_region: str = "us-east-2",
        environment: str = "development",
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Lookup hosted zone for the domain
        hosted_zone = lookup_hosted_zone(
            self,
            stack_id=id,
            hosted_zone_domain_name=hosted_zone_domain_name,
        )

        # Certificates (exposed as stack attributes for use in other stacks/tests)
        self.website_certificate = AcmCertificate(
            self,
            "WebsiteCertificate",
            domain_name=domain_name,
            hosted_zone=hosted_zone,
            include_wildcard_san=environment == "preview",
        )

        # Store certificate ARNs in SSM Parameters
        ssm.StringParameter(
            self,
            "WebsiteCertArnParam",
            parameter_name=ssm_params["website_cert_arn_param"],
            string_value=self.website_certificate.certificate.certificate_arn,
        )

        # Replicate SSM Parameters to a secondary region
        replication_config = build_ssm_replication_config(
            [ssm_params["website_cert_arn_param"]]
        )

        SSMParameterReplicator(
            self,
            "ACMCertsSSMReplicatorV2",
            source_region=env_region,
            target_region=replication_target_region,
            param_path_prefix=replication_config.param_path_prefix,
            parameters=replication_config.parameters,
        )
