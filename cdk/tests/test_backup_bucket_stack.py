import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from stacks.backup_website_bucket import BackupWebsiteBucket


@pytest.fixture
def backup_stack():
    app = App()
    region = "us-east-1"
    env = Environment(account="111111111111", region=region)

    ssm_params = {
        "backup_website_bucket_arn_param": "/dummy/backup/arn",
        "backup_website_bucket_name_param": "/dummy/backup/name",
        "backup_website_bucket_domain_name_param": "/dummy/backup/domain",
    }

    stack = BackupWebsiteBucket(
        scope=app,
        id="TestBackupWebsiteBucket",
        ssm_params=ssm_params,
        region=region,
        env=env,
        cross_region_references=True,
    )
    return stack


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

    # Fetch all IAM policies
    policies = template.find_resources("AWS::IAM::Policy")

    # Flatten all statements into one list
    all_statements = []
    for policy in policies.values():
        stmts = policy["Properties"]["PolicyDocument"]["Statement"]
        if isinstance(stmts, list):
            all_statements.extend(stmts)
        else:
            all_statements.append(stmts)

    # Collect all allowed actions
    actions = []
    for stmt in all_statements:
        if stmt.get("Effect") == "Allow":
            action = stmt.get("Action")
            if isinstance(action, list):
                actions.extend(action)
            elif isinstance(action, str):
                actions.append(action)

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

    policies = template.find_resources("AWS::IAM::Policy")
    ssm_resources = []
    for policy in policies.values():
        stmts = policy["Properties"]["PolicyDocument"]["Statement"]
        stmts = stmts if isinstance(stmts, list) else [stmts]
        for stmt in stmts:
            if stmt.get("Effect") != "Allow":
                continue
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            if any(a.startswith("ssm:") for a in actions):
                resource = stmt.get("Resource", [])
                if isinstance(resource, str):
                    resource = [resource]
                ssm_resources.extend(resource)

    # Every scoped SSM resource must end with /* so sub-parameters are covered
    for resource in ssm_resources:
        if isinstance(resource, str) and ":parameter/" in resource:
            assert resource.endswith(
                "/*"
            ), f"SSM IAM resource missing trailing /* wildcard: {resource}"
