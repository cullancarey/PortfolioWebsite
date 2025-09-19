import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from stacks.website_stack import Website


@pytest.fixture
def website_stack():
    app = App()
    account_id = "111111111111"
    region = "us-east-1"
    env = Environment(account=account_id, region=region)

    acm_ssm_params = {
        "website_cert_arn_param": "/dummy/acm/website-cert-arn",
        "contact_form_cert_arn_param": "/dummy/acm/contact-form-cert-arn",
    }
    backup_ssm_params = {
        "backup_website_bucket_arn_param": "/dummy/backup/arn",
        "backup_website_bucket_name_param": "/dummy/backup/name",
        "backup_website_bucket_domain_name_param": "/dummy/backup/domain",
    }

    stack = Website(
        scope=app,
        id="TestWebsite",
        account_id=account_id,
        region=region,
        domain_name="example.com",
        source_file_path="tests/assets",
        environment="development",
        acm_ssm_params=acm_ssm_params,
        backup_website_bucket_ssm_params=backup_ssm_params,
        env=env,
        cross_region_references=True,
    )
    return stack


def test_cloudfront_distribution_settings(website_stack):
    template = Template.from_stack(website_stack)

    template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": {
                "DefaultRootObject": "index.html",
                "Enabled": True,
                "Comment": "Distribution for example.com",
            }
        },
    )


def test_cloudfront_error_responses(website_stack):
    template = Template.from_stack(website_stack)

    template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": {
                "CustomErrorResponses": [
                    {"ErrorCode": 403, "ResponsePagePath": "/error.html"},
                    {"ErrorCode": 404, "ResponsePagePath": "/error.html"},
                    {"ErrorCode": 500, "ResponsePagePath": "/error.html"},
                    {"ErrorCode": 502, "ResponsePagePath": "/error.html"},
                    {"ErrorCode": 503, "ResponsePagePath": "/error.html"},
                    {"ErrorCode": 504, "ResponsePagePath": "/error.html"},
                ]
            }
        },
    )


def test_route53_records_created(website_stack):
    template = Template.from_stack(website_stack)

    template.resource_count_is("AWS::Route53::RecordSet", 3)  # root, www, form.


def test_bucket_deployments_exist(website_stack):
    template = Template.from_stack(website_stack)

    template.resource_count_is("Custom::CDKBucketDeployment", 2)


def test_bucket_policy_enforces_tls(website_stack):
    template = Template.from_stack(website_stack)

    policies = template.find_resources("AWS::S3::BucketPolicy")
    found_tls = False

    for _, policy in policies.items():
        for stmt in policy["Properties"]["PolicyDocument"]["Statement"]:
            if stmt.get("Sid") == "EnforceTLS":
                found_tls = True
                assert stmt["Effect"] == "Deny"
                assert stmt["Action"] == "s3:*"
                assert stmt["Principal"] == {"AWS": "*"}
                assert stmt["Condition"] == {"Bool": {"aws:SecureTransport": "false"}}

    assert found_tls, "No EnforceTLS statement found in bucket policies"


def test_cloudfront_uses_oac(website_stack):
    """
    Validate that CloudFront is using an Origin Access Control (OAC),
    which replaces the older OAI + bucket policy approach.
    """
    template = Template.from_stack(website_stack)

    # Ensure exactly one OAC is present
    template.resource_count_is("AWS::CloudFront::OriginAccessControl", 1)

    # Verify OAC has correct settings
    template.has_resource_properties(
        "AWS::CloudFront::OriginAccessControl",
        {
            "OriginAccessControlConfig": {
                "OriginAccessControlOriginType": "s3",
                "SigningBehavior": "always",
                "SigningProtocol": "sigv4",
            }
        },
    )
