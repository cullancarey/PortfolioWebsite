from aws_cdk import (
    aws_apigatewayv2 as apigw,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_ssm as ssm,
    Duration,
)
from constructs import Construct


class ApiGwtoLambda(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        account_id: str,
        region: str,
        domain_name: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Lambda Function (Assuming that this is previously created)
        contact_form_lambda = _lambda.DockerImageFunction(
            self,
            f"ContactFormLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                "assets/lambda/contact_form_intake/"
            ),
            timeout=Duration.seconds(30),
            architecture=_lambda.Architecture.X86_64,
            environment={"environment": environment, "website": domain_name},
        )

        # API Gateway HTTP API
        self.contact_form_api = apigw.CfnApi(
            self,
            f"ContactFormApi",
            name="ContactFormApi",
            description=f"API gateway resource for intake of the contact form on {domain_name}",
            cors_configuration=apigw.CfnApi.CorsProperty(
                allow_credentials=False,
                allow_headers=["*"],
                allow_methods=["POST", "OPTIONS"],
                allow_origins=["*"],
            ),
            protocol_type="HTTP",
        )

        apigw.CfnStage(
            self,
            "ContactFormApiStage",
            api_id=self.contact_form_api.attr_api_id,
            stage_name="$default",
            auto_deploy=True,
            description="Stage for api gateway resource that intakes the websites contact form.",
        )

        # API Gateway Integration
        contact_form_integration = apigw.CfnIntegration(
            self,
            f"ContactFormApiIntegration",
            api_id=self.contact_form_api.attr_api_id,
            description="Integration for form intake api and form intake lambda.",
            integration_type="AWS_PROXY",
            integration_method="POST",
            connection_type="INTERNET",
            integration_uri=contact_form_lambda.function_arn,
            payload_format_version="2.0",
        )

        cfn_route = apigw.CfnRoute(
            self,
            f"ContactFormApiRoute",
            api_id=self.contact_form_api.attr_api_id,
            route_key="POST /",
            target=f"integrations/{contact_form_integration.ref}",
        )

        contact_form_lambda.add_permission(
            id="AllowAPIgatewayInvokation",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=account_id,
            source_arn=f"arn:aws:execute-api:{region}:{account_id}:{self.contact_form_api.attr_api_id}/*/*/",
        )

        ssm.StringParameter.from_secure_string_parameter_attributes(
            self,
            id="GoogleCaptchaParam",
            parameter_name=f"{environment}_google_captcha_secret",
        ).grant_read(contact_form_lambda)

        ses_policy_statement = iam.PolicyStatement(
            sid="SESPermissions",
            effect=iam.Effect.ALLOW,
            actions=["ses:SendEmail"],
            resources=[
                f"arn:aws:ses:us-east-2:{account_id}:identity/{domain_name.replace('form.', '')}",
                f"arn:aws:ses:us-east-2:{account_id}:identity/cullancarey@yahoo.com",
                f"arn:aws:ses:us-east-2:{account_id}:identity/cullancareyconsulting@gmail.com",
            ],
        )

        contact_form_lambda.add_to_role_policy(statement=ses_policy_statement)
