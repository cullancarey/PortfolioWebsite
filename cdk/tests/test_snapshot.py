import json
from aws_cdk.assertions import Template


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
