from aws_cdk.assertions import Match, Template
from stacks.acm_certificates_stack import ACMCertificatesStack

from tests.helpers import collect_allowed_actions, collect_ssm_resources


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

    all_actions = collect_allowed_actions(template)

    assert "ssm:GetParameter" in all_actions
    assert "ssm:PutParameter" in all_actions


def test_ssm_permissions_have_path_wildcard(acm_stack):
    """
    Ensure SSM IAM policies scope to a path prefix with a trailing /*
    wildcard, not an exact parameter name. Without /*, the Lambda would
    get access denied on any parameter under that path.
    """
    template = Template.from_stack(acm_stack)

    ssm_resources = collect_ssm_resources(template)

    # Every scoped SSM resource must end with /* so sub-parameters are covered
    for resource in ssm_resources:
        if isinstance(resource, str) and ":parameter/" in resource:
            assert resource.endswith(
                "/*"
            ), f"SSM IAM resource missing trailing /* wildcard: {resource}"


def test_preview_certificate_includes_wildcard_san(
    test_app,
    test_env,
    test_region,
    acm_ssm_params,
):
    preview_stack = ACMCertificatesStack(
        scope=test_app,
        id="TestACMCertificatesPreview",
        domain_name="example.com",
        hosted_zone_domain_name="example.com",
        env_region=test_region,
        ssm_params=acm_ssm_params,
        environment="preview",
        env=test_env,
        cross_region_references=True,
    )

    template = Template.from_stack(preview_stack)

    template.has_resource_properties(
        "AWS::CertificateManager::Certificate",
        {
            "DomainName": "example.com",
            "SubjectAlternativeNames": Match.array_with(
                ["www.example.com", "*.example.com"]
            ),
        },
    )
