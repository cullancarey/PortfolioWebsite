"""SSM Parameter replication construct for cross-region disaster recovery.

Uses a Lambda function to replicate SSM parameters from a source region to
a target region. Useful for replicating certificates, configuration, and
other parameters needed for failover infrastructure.
"""

from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    custom_resources as cr,
    CustomResource,
)
from constructs import Construct
import json
from typing import List, Dict


class SSMParameterReplicator(Construct):
    """Replicates AWS Systems Manager parameters across AWS regions.

    Uses a Lambda function triggered by a CloudFormation custom resource to
    replicate specified SSM parameters from a source region to a target region.
    This is essential for disaster recovery and cross-region failover scenarios.

    The Lambda function has least-privilege IAM permissions scoped to specific
    parameter paths.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        source_region: str,
        target_region: str,
        parameters: List[Dict[str, str]],
        param_path_prefix: str = "",
        **kwargs,
    ) -> None:
        """Initialize the SSMParameterReplicator construct.

        Args:
            scope: The scope/parent construct
            id: The logical ID of the construct
            source_region: AWS region to read parameters from
            target_region: AWS region to write parameters to
            parameters: List of dicts with 'source' and 'target' parameter names
                       Example: [{'source': '/param1', 'target': '/param1'}]
            param_path_prefix: Optional path prefix for IAM permission scoping
            **kwargs: Additional keyword arguments passed to the parent Construct
        """
        super().__init__(scope, id, **kwargs)

        # Create CloudWatch log group for Lambda execution logs
        replicate_ssm_log_group = logs.LogGroup(
            self, "SSMParamReplicatorLogGroup", retention=logs.RetentionDays.ONE_YEAR
        )

        # Docker-based Lambda function that performs the replication
        # Using Docker image allows us to include custom dependencies if needed
        replicate_ssm_lambda = _lambda.DockerImageFunction(
            self,
            "SSMParamReplicatorLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                "assets/lambdas/ssm_param_replicator/"
            ),
            timeout=Duration.seconds(60),
            architecture=_lambda.Architecture.X86_64,
            environment={
                "SOURCE_REGION": source_region,
                "TARGET_REGION": target_region,
                "PARAMETERS": json.dumps(parameters),
            },
            log_group=replicate_ssm_log_group,
        )

        # Add IAM permissions following least-privilege principle
        # Permissions are scoped to specific parameter path prefix if provided
        # SSM ARNs do not include a leading slash, but wildcard suffix is required
        # for prefix matching (e.g., parameter/ACMCertificates/*)
        if param_path_prefix:
            prefix = param_path_prefix.lstrip("/")
            src_resource = (
                f"arn:aws:ssm:{source_region}:{scope.account}:parameter/{prefix}/*"
            )
            dst_resource = (
                f"arn:aws:ssm:{target_region}:{scope.account}:parameter/{prefix}/*"
            )
        else:
            src_resource = f"arn:aws:ssm:{source_region}:{scope.account}:parameter/*"
            dst_resource = f"arn:aws:ssm:{target_region}:{scope.account}:parameter/*"

        # Allow reading from source region SSM
        replicate_ssm_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[src_resource],
            )
        )

        # Allow writing to target region SSM
        replicate_ssm_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:PutParameter"],
                resources=[dst_resource],
            )
        )

        # Create CloudFormation custom resource provider
        # This wraps the Lambda in a CloudFormation-compatible interface
        provider = cr.Provider(
            self,
            "ReplicateSSMProvider",
            on_event_handler=replicate_ssm_lambda,
        )

        # Create the custom resource that triggers replication during stack creation
        CustomResource(
            self,
            "ReplicateSSMCustomResource",
            service_token=provider.service_token,
        )
