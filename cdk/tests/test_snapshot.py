import pytest
import json
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from stacks.backup_website_bucket import BackupWebsiteBucket
from stacks.acm_certificates_stack import ACMCertificates
from stacks.website_stack import Website


@pytest.fixture
def stacks():
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

    backup_stack = BackupWebsiteBucket(
        scope=app,
        id="TestBackupWebsiteBucket",
        ssm_params=backup_ssm_params,
        region=region,
        env=env,
        cross_region_references=True,
    )

    acm_stack = ACMCertificates(
        scope=app,
        id="TestACMCertificates",
        account_id=account_id,
        domain_name="example.com",
        env_region=region,
        ssm_params=acm_ssm_params,
        env=env,
        cross_region_references=True,
    )

    website_stack = Website(
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

    return backup_stack, acm_stack, website_stack


def test_templates_snapshot(snapshot, stacks):
    backup_stack, acm_stack, website_stack = stacks

    backup_template = json.dumps(
        Template.from_stack(backup_stack).to_json(), indent=2, sort_keys=True
    )
    acm_template = json.dumps(
        Template.from_stack(acm_stack).to_json(), indent=2, sort_keys=True
    )
    website_template = json.dumps(
        Template.from_stack(website_stack).to_json(), indent=2, sort_keys=True
    )

    snapshot.assert_match(backup_template, "backup_bucket_snapshot")
    snapshot.assert_match(acm_template, "acm_certificate_snapshot")
    snapshot.assert_match(website_template, "website_snapshot")
