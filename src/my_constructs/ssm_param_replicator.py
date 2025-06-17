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


class SsmParameterReplicator(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        source_region: str,
        target_region: str,
        parameters: list,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        replicate_ssm_lambda = _lambda.DockerImageFunction(
            self,
            "SSMParamReplicatorLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                "assets/lambda/ssm_param_replicator/"
            ),
            timeout=Duration.seconds(60),
            architecture=_lambda.Architecture.X86_64,
            environment={
                "SOURCE_REGION": source_region,
                "TARGET_REGION": target_region,
                "PARAMETERS": json.dumps(parameters),
            },
            log_retention=logs.RetentionDays.ONE_YEAR,
        )

        # Add required permissions to the auto-generated role
        replicate_ssm_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["arn:aws:logs:*:*:*"],
            )
        )

        replicate_ssm_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[f"arn:aws:ssm:{source_region}:{scope.account}:parameter/*"],
            )
        )

        replicate_ssm_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:PutParameter"],
                resources=[f"arn:aws:ssm:{target_region}:{scope.account}:parameter/*"],
            )
        )

        provider = cr.Provider(
            self,
            "ReplicateSSMProvider",
            on_event_handler=replicate_ssm_lambda,
        )

        CustomResource(
            self,
            "ReplicateSSMCustomResource",
            service_token=provider.service_token,
        )
