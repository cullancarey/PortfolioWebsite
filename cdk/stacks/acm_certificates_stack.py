import boto3
from botocore.exceptions import ClientError

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
        # For preview environments, check if parameter already exists to avoid
        # Early Validation hook errors on re-deployment
        param_name = ssm_params["website_cert_arn_param"]
        cert_param_exists = self._parameter_exists(param_name, env_region)

        if cert_param_exists:
            # Import existing parameter; it will be updated by replicator or manually
            ssm.StringParameter.from_string_parameter_attributes(
                self,
                "WebsiteCertArnParam",
                parameter_name=param_name,
                type=ssm.ParameterType.STRING,
                simple_name=False,
            )
        else:
            # Create new parameter
            ssm.StringParameter(
                self,
                "WebsiteCertArnParam",
                parameter_name=param_name,
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

    @staticmethod
    def _parameter_exists(parameter_name: str, region: str) -> bool:
        """Check if an SSM parameter exists in the specified region.

        Args:
            parameter_name: The name of the SSM parameter
            region: The AWS region to check

        Returns:
            True if the parameter exists, False otherwise
        """
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            ssm_client.get_parameter(Name=parameter_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                return False
            # For any other error (e.g., auth), assume parameter doesn't exist
            # to allow CDK to attempt creation
            return False
        except Exception:
            # If we can't connect/check, assume it doesn't exist
            return False
