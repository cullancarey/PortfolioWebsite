import os
import json
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from stacks.acm_certificates_stack import ACMCertificates
from stacks.backup_website_bucket import BackupWebsiteBucket
from stacks.website_stack import Website


# Define the path to the JSON file
json_file_path = os.path.join(os.path.dirname(__file__), "..", "cdk.context.json")

# Read the JSON file and load it into a Python dictionary
with open(json_file_path, "r") as f:
    data = json.load(f)

# Access the 'environment' section
environment = "development"
development_data = data.get(environment, {})

# Assign variables based on the JSON values
account_id = development_data.get("account_id", "default_account_id")
region = development_data.get("region", "default_region")
domain_name = development_data.get("domain_name", "default_domain_name")
file_path = development_data.get("file_path", "default_file_path")


env = Environment(account=account_id, region=region)

cloudfront_region = "us-east-1"
cloudfront_env = Environment(account=account_id, region=cloudfront_region)
app = App()


def test_acm_certificates_stack(snapshot):
    # Create an instance of BackupWebsiteBucket stack
    backup_website_bucket_stack = BackupWebsiteBucket(
        scope=app,
        id="TestBackupWebsiteBucket",
        env=cloudfront_env,
        cross_region_references=True,
    )

    # Create an instance of ACMCertificates stack
    acm_certificates_stack = ACMCertificates(
        scope=app,
        id="TestACMCertificates",
        account_id=account_id,
        domain_name=domain_name,
        env=cloudfront_env,
        cross_region_references=True,
    )

    # Create an instance of Website stack
    website_stack = Website(
        scope=app,
        id="TestWebsite",
        account_id=account_id,
        region=region,
        domain_name=domain_name,
        source_file_path=file_path,
        environment=environment,
        website_certificate=acm_certificates_stack.website_certificate.certificate,
        contact_form_certificate=acm_certificates_stack.contact_form_certificate.certificate,
        backup_website_bucket=backup_website_bucket_stack.backup_website_bucket.bucket,
        env=env,
        cross_region_references=True,
    )

    # Generate CloudFormation templates for each stack
    backup_website_bucket_stack_template = Template.from_stack(
        backup_website_bucket_stack
    )
    acm_certificates_stack_template = Template.from_stack(acm_certificates_stack)
    website_stack_template = Template.from_stack(website_stack)

    # Assert that the generated templates match the saved snapshots
    assert acm_certificates_stack_template.to_json() == snapshot(
        name="acm_certificate_snapshot"
    )
    assert backup_website_bucket_stack_template.to_json() == snapshot(
        name="backup_bucket_snapshot"
    )
    assert website_stack_template.to_json() == snapshot(name="website_snapshot")
