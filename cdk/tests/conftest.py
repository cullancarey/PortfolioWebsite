from __future__ import annotations

from pathlib import Path
import sys

import pytest
from aws_cdk import App, Environment

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stacks.acm_certificates_stack import ACMCertificatesStack
from stacks.backup_website_bucket import BackupWebsiteBucketStack
from stacks.website_stack import WebsiteStack


@pytest.fixture(scope="session")
def test_account_id() -> str:
    return "111111111111"


@pytest.fixture(scope="session")
def test_region() -> str:
    return "us-east-1"


@pytest.fixture()
def test_env(test_account_id: str, test_region: str) -> Environment:
    return Environment(account=test_account_id, region=test_region)


@pytest.fixture(scope="session")
def acm_ssm_params() -> dict[str, str]:
    return {
        "website_cert_arn_param": "/dummy/acm/website-cert-arn",
    }


@pytest.fixture(scope="session")
def backup_ssm_params() -> dict[str, str]:
    return {
        "backup_website_bucket_arn_param": "/dummy/backup/arn",
        "backup_website_bucket_name_param": "/dummy/backup/name",
        "backup_website_bucket_domain_name_param": "/dummy/backup/domain",
    }


@pytest.fixture()
def test_app() -> App:
    return App()


@pytest.fixture()
def acm_stack(
    test_app: App,
    test_env: Environment,
    test_region: str,
    acm_ssm_params: dict[str, str],
) -> ACMCertificatesStack:
    return ACMCertificatesStack(
        scope=test_app,
        id="TestACMCertificates",
        domain_name="example.com",
        env_region=test_region,
        ssm_params=acm_ssm_params,
        env=test_env,
        cross_region_references=True,
    )


@pytest.fixture()
def backup_stack(
    test_app: App,
    test_env: Environment,
    test_region: str,
    backup_ssm_params: dict[str, str],
) -> BackupWebsiteBucketStack:
    return BackupWebsiteBucketStack(
        scope=test_app,
        id="TestBackupWebsiteBucket",
        ssm_params=backup_ssm_params,
        region=test_region,
        env=test_env,
        cross_region_references=True,
    )


@pytest.fixture()
def website_stack(
    test_app: App,
    test_env: Environment,
    acm_ssm_params: dict[str, str],
    backup_ssm_params: dict[str, str],
) -> WebsiteStack:
    return WebsiteStack(
        scope=test_app,
        id="TestWebsite",
        domain_name="example.com",
        source_file_path="tests/assets",
        acm_ssm_params=acm_ssm_params,
        backup_website_bucket_ssm_params=backup_ssm_params,
        env=test_env,
        cross_region_references=True,
    )


@pytest.fixture()
def stacks(
    acm_stack: ACMCertificatesStack,
    backup_stack: BackupWebsiteBucketStack,
    website_stack: WebsiteStack,
):
    return backup_stack, acm_stack, website_stack
