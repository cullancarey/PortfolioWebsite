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
        hosted_zone: route53.IHostedZone,
        include_wildcard_san: bool = False,
        **kwargs,
    ) -> None:
        """Initialize the AcmCertificate construct.

        Args:
            scope: The scope/parent construct
            id: The logical ID of the construct
            domain_name: The primary domain name for the certificate (e.g., 'example.com')
            hosted_zone: The Route53 hosted zone for DNS validation
            include_wildcard_san: If True, include *.domain_name as a SAN (useful for preview envs)
            **kwargs: Additional keyword arguments passed to the parent Construct
        """
        super().__init__(scope, id, **kwargs)

        # Build subject alternative names
        # Standard: always include www.{domain_name}
        # Preview mode: include *.{domain_name} for wildcard subdomains
        subject_alternative_names = [f"www.{domain_name}"]
        if include_wildcard_san:
            subject_alternative_names.append(f"*.{domain_name}")

        # Create ACM certificate with DNS validation and transparency logging
        self.certificate = acm.Certificate(
            self,
            f"AcmCertificate",
            domain_name=domain_name,
            subject_alternative_names=subject_alternative_names,
            validation=acm.CertificateValidation.from_dns(hosted_zone),
            transparency_logging_enabled=True,
        )
