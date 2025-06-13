from aws_cdk import Stack, aws_route53 as route53, aws_ssm as ssm
from constructs import Construct
from my_constructs.acm_certificate import AcmCertificate
from my_constructs.ssm_param_replicator import SsmParameterReplicator


class ACMCertificates(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        account_id: str,
        domain_name: str,
        env_region: str,
        ssm_params: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        hosted_zone = route53.HostedZone.from_lookup(
            self, f"{id}-HostedZone", domain_name=domain_name
        )

        website_cert = AcmCertificate(
            self,
            "WebsiteCertificate",
            account_id=account_id,
            domain_name=domain_name,
            hosted_zone=hosted_zone,
        )

        contact_form_cert = AcmCertificate(
            self,
            "ContactFormCertificate",
            account_id=account_id,
            domain_name=f"form.{domain_name}",
            hosted_zone=hosted_zone,
        )

        website_cert_arn_param = ssm.StringParameter(
            self,
            "WebsiteCertArnParam",
            parameter_name=ssm_params["website_cert_arn_param"],
            string_value=website_cert.certificate.certificate_arn,
        )

        contact_form_cert_arn_param = ssm.StringParameter(
            self,
            "ContactFormCertArnParam",
            parameter_name=ssm_params["contact_form_cert_arn_param"],
            string_value=contact_form_cert.certificate.certificate_arn,
        )

        SsmParameterReplicator(
            self,
            "ACMCertsSSMReplicator",
            source_region=env_region,
            target_region="us-east-2",
            parameters=[
                {
                    "source": website_cert_arn_param.parameter_name,
                    "target": website_cert_arn_param.parameter_name,
                },
                {
                    "source": contact_form_cert_arn_param.parameter_name,
                    "target": contact_form_cert_arn_param.parameter_name,
                },
            ],
        )
