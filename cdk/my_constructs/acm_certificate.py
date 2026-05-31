"""ACM certificate construct for HTTPS/TLS certificate management.

Provides a public SSL/TLS certificate from AWS Certificate Manager with
DNS validation and transparency logging enabled.
"""

from aws_cdk import aws_certificatemanager as acm, aws_route53 as route53
from constructs import Construct


class AcmCertificate(Construct):
    """AWS Certificate Manager (ACM) certificate construct.

    Creates a public SSL/TLS certificate with automatic DNS validation
    and Certificate Transparency (CT) logging enabled. The certificate
    is automatically renewed 30-60 days before expiration.

    Attributes:
        certificate (acm.Certificate): The ACM certificate resource
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        hosted_zone: route53.HostedZone,
        **kwargs,
    ) -> None:
        """Initialize the AcmCertificate construct.

        Args:
            scope: The scope/parent construct
            id: The logical ID of the construct
            domain_name: The primary domain name for the certificate (e.g., 'example.com')
            hosted_zone: The Route53 hosted zone for DNS validation
            **kwargs: Additional keyword arguments passed to the parent Construct
        """
        super().__init__(scope, id, **kwargs)

        # Create ACM certificate with DNS validation and transparency logging
        self.certificate = acm.Certificate(
            self,
            f"AcmCertificate",
            domain_name=domain_name,
            subject_alternative_names=[f"www.{domain_name}"],
            validation=acm.CertificateValidation.from_dns(hosted_zone),
            transparency_logging_enabled=True,
        )
