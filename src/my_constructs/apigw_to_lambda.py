from aws_cdk import (
    Duration,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_iam as iam,
    aws_ssm as ssm,
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

        # Lambda for contact form intake
        contact_form_log_group = logs.LogGroup(
            self, "ContactFormLogGroup", retention=logs.RetentionDays.ONE_YEAR
        )

        contact_form_lambda = _lambda.DockerImageFunction(
            self,
            "ContactFormLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                "assets/lambdas/contact_form_intake/"
            ),
            timeout=Duration.seconds(30),
            architecture=_lambda.Architecture.X86_64,
            environment={"environment": environment, "website": domain_name},
            log_group=contact_form_log_group,
        )

        # API Gateway HTTP API
        self.contact_form_api = apigw.HttpApi(
            self,
            "ContactFormApi",
            description=f"API gateway resource for intake of the contact form on {domain_name}",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_headers=["*"],
                allow_methods=[apigw.CorsHttpMethod.POST, apigw.CorsHttpMethod.OPTIONS],
                allow_origins=["*"],
                allow_credentials=False,
            ),
        )

        # Access Log Group for API Gateway
        api_log_group = logs.LogGroup(
            self, "ContactFormApiLogGroup", retention=logs.RetentionDays.ONE_YEAR
        )

        # Enable logging on default stage
        self.contact_form_api.default_stage.node.default_child.add_override(
            "Properties.AccessLogSettings",
            {
                "DestinationArn": api_log_group.log_group_arn,
                "Format": '{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","user":"$context.identity.user","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","path":"$context.path","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength"}',
            },
        )

        # API Gateway Integration with Lambda
        contact_form_integration = apigw_integrations.HttpLambdaIntegration(
            "ContactFormApiIntegration", handler=contact_form_lambda
        )

        # Attach Route
        self.contact_form_api.add_routes(
            path="/",
            methods=[apigw.HttpMethod.POST],
            integration=contact_form_integration,
        )

        # Allow API Gateway to invoke the Lambda
        contact_form_lambda.add_permission(
            "AllowAPIgatewayInvocation",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=account_id,
            source_arn=f"arn:aws:execute-api:{region}:{account_id}:{self.contact_form_api.http_api_id}/*/*/",
        )

        # Allow Lambda to read Captcha Secret from SSM
        ssm.StringParameter.from_secure_string_parameter_attributes(
            self,
            "GoogleCaptchaParam",
            parameter_name=f"{environment}_google_captcha_secret",
        ).grant_read(contact_form_lambda)

        # Allow Lambda to send emails via SES
        ses_policy_statement = iam.PolicyStatement(
            sid="SESPermissions",
            effect=iam.Effect.ALLOW,
            actions=["ses:SendEmail"],
            resources=[
                f"arn:aws:ses:us-east-2:{account_id}:identity/{domain_name.replace('form.', '')}",
                f"arn:aws:ses:us-east-2:{account_id}:identity/cullancarey@yahoo.com",
                f"arn:aws:ses:us-east-2:{account_id}:identity/cullancareyconsulting@gmail.com",
                f"arn:aws:ses:us-east-2:{account_id}:configuration-set/cullancarey",
            ],
        )

        contact_form_lambda.add_to_role_policy(ses_policy_statement)
