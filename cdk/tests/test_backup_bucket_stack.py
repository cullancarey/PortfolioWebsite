from aws_cdk.assertions import Template

from tests.helpers import collect_allowed_actions, collect_ssm_resources


def test_bucket_has_encryption(backup_stack):
    template = Template.from_stack(backup_stack)
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            }
        },
    )


def test_bucket_has_lifecycle_and_tls(backup_stack):
    template = Template.from_stack(backup_stack)

    # Lifecycle rule exists
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "LifecycleConfiguration": {
                "Rules": [
                    {
                        "NoncurrentVersionExpiration": {"NoncurrentDays": 2},
                        "Status": "Enabled",
                    }
                ]
            }
        },
    )

    # TLS enforcement policy
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Sid": "EnforceTLS",
                        "Effect": "Deny",
                        "Action": "s3:*",
                        "Principal": {"AWS": "*"},
                        "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                    }
                ]
            }
        },
    )


def test_ssm_parameters_created(backup_stack):
    template = Template.from_stack(backup_stack)

    template.resource_count_is("AWS::SSM::Parameter", 3)
    template.has_resource_properties(
        "AWS::SSM::Parameter", {"Name": "/dummy/backup/arn"}
    )
    template.has_resource_properties(
        "AWS::SSM::Parameter", {"Name": "/dummy/backup/name"}
    )
    template.has_resource_properties(
        "AWS::SSM::Parameter", {"Name": "/dummy/backup/domain"}
    )


def test_replicator_lambda_configuration(backup_stack):
    template = Template.from_stack(backup_stack)

    # Ensure Lambda functions exist (the replicator handlers)
    template.resource_count_is("AWS::Lambda::Function", 2)

    # Ensure environment variables are present
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

    actions = collect_allowed_actions(template)

    # Assert the critical actions exist
    assert "ssm:GetParameter" in actions
    assert "ssm:PutParameter" in actions


def test_ssm_permissions_have_path_wildcard(backup_stack):
    """
    Ensure SSM IAM policies scope to a path prefix with a trailing /*
    wildcard, not an exact parameter name. Without /*, the Lambda would
    get access denied on any parameter under that path.
    """
    template = Template.from_stack(backup_stack)

    ssm_resources = collect_ssm_resources(template)

    # Every scoped SSM resource must end with /* so sub-parameters are covered
    for resource in ssm_resources:
        if isinstance(resource, str) and ":parameter/" in resource:
            assert resource.endswith(
                "/*"
            ), f"SSM IAM resource missing trailing /* wildcard: {resource}"
