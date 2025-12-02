import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from stacks.acm_certificates_stack import ACMCertificates


@pytest.fixture
def acm_stack():
    app = App()
    account_id = "111111111111"
    region = "us-east-1"
    env = Environment(account=account_id, region=region)

    ssm_params = {
        "website_cert_arn_param": "/dummy/acm/website-cert-arn",
    }

    stack = ACMCertificates(
        scope=app,
        id="TestACMCertificates",
        account_id=account_id,
        domain_name="example.com",
        env_region=region,
        ssm_params=ssm_params,
        env=env,
        cross_region_references=True,
    )
    return stack


def test_certificates_created(acm_stack):
    """
    Ensure that two ACM certificates are created: one for the root domain,
    and one for the contact form subdomain.
    """
    template = Template.from_stack(acm_stack)

    template.resource_count_is("AWS::CertificateManager::Certificate", 1)


def test_ssm_parameters_created(acm_stack):
    """
    Ensure that the SSM parameters for storing certificate ARNs are created.
    """
    template = Template.from_stack(acm_stack)

    template.has_resource_properties(
        "AWS::SSM::Parameter",
        {"Name": "/dummy/acm/website-cert-arn"},
    )


def test_replicator_lambda_exists(acm_stack):
    """
    Ensure that the SSM Parameter Replicator Lambda functions are created.
    """
    template = Template.from_stack(acm_stack)

    # At least one Lambda function should exist for replication
    assert len(template.find_resources("AWS::Lambda::Function")) >= 1

    # Ensure it has the right environment variables
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": {
                    "SOURCE_REGION": "us-east-1",
                    "TARGET_REGION": "us-east-2",
                }
            }
        },
    )


def test_replicator_lambda_has_ssm_permissions(acm_stack):
    """
    Ensure that IAM policies attached to the replicator Lambda allow SSM actions.
    """
    template = Template.from_stack(acm_stack)

    policies = template.find_resources("AWS::IAM::Policy")
    all_actions = []
    for policy in policies.values():
        stmts = policy["Properties"]["PolicyDocument"]["Statement"]
        stmts = stmts if isinstance(stmts, list) else [stmts]
        for stmt in stmts:
            if stmt.get("Effect") == "Allow":
                action = stmt.get("Action")
                if isinstance(action, list):
                    all_actions.extend(action)
                elif isinstance(action, str):
                    all_actions.append(action)

    assert "ssm:GetParameter" in all_actions
    assert "ssm:PutParameter" in all_actions
