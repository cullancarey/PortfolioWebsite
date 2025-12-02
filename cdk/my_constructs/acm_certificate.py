from aws_cdk import aws_certificatemanager as acm, aws_route53 as route53
from constructs import Construct


class AcmCertificate(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        hosted_zone: route53.HostedZone,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ACM Certificate
        self.certificate = acm.Certificate(
            self,
            f"AcmCertificate",
            domain_name=domain_name,
            subject_alternative_names=[f"www.{domain_name}"],
            validation=acm.CertificateValidation.from_dns(hosted_zone),
            transparency_logging_enabled=True,
        )
