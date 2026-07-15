# Python CDK Stacks for AWS Services

This directory contains Python CDK stacks for the PortfolioWebsite infrastructure.

## Table of Contents

- [ACMCertificates](#acmcertificates)
- [BackupWebsiteBucket](#backupwebsitebucket)
- [Website](#website)

## ACMCertificates

Creates the ACM certificate for the primary domain and replicates its ARN to a secondary region via SSM Parameter Store.

### Parameters

- `domain_name`: The primary domain name for the certificate.
- `env_region`: The AWS region where the stack is deployed.
- `ssm_params`: Dict of SSM parameter names (e.g., `website_cert_arn_param`).
- `replication_target_region` _(optional)_: Region to replicate the certificate ARN to. Defaults to `us-east-2`.

### Features

- Creates an ACM certificate (with `www.<domain>` SAN) via the `AcmCertificate` construct.
- Stores the certificate ARN in SSM Parameter Store.
- Replicates the SSM parameter to a secondary region using `SSMParameterReplicator`.

## BackupWebsiteBucket

Creates the S3 backup bucket used as the CloudFront failover origin, and replicates its metadata to a secondary region via SSM Parameter Store.

### Parameters

- `ssm_params`: Dict of SSM parameter names for bucket ARN, name, and domain name.
- `region`: The AWS region where the stack is deployed.
- `replication_target_region` _(optional)_: Region to replicate SSM parameters to. Defaults to `us-east-2`.

### Features

- Creates a secure S3 bucket via the `S3Bucket` construct.
- Adds a bucket policy allowing CloudFront OAC read access for all distributions in the account.
- Stores the bucket ARN, name, and regional domain name in SSM Parameter Store.
- Replicates all three SSM parameters to a secondary region using `SSMParameterReplicator`.

## Website

Creates the primary website infrastructure: S3 bucket, CloudFront distribution, Route53 DNS records, and static asset deployments.

### Parameters

- `domain_name`: The primary domain name for the website.
- `source_file_path`: Path to the built frontend assets to deploy.
- `acm_ssm_params`: Dict with `website_cert_arn_param` — SSM parameter name for the ACM certificate ARN.
- `backup_website_bucket_ssm_params`: Dict with `backup_website_bucket_arn_param` and `backup_website_bucket_name_param` — SSM parameter names for the backup bucket.
- `geo_restrictions` _(optional)_: Geographic restriction config passed to `CloudFrontDistribution`.
- `cloudfront_price_class` _(optional)_: CloudFront price class. Defaults to `PRICE_CLASS_100`.

### Features

- Creates a primary website S3 bucket.
- Sets up a `CloudFrontDistribution` with the primary bucket and backup bucket as an origin group.
- Creates Route53 A records for the root domain and `www` subdomain.
- Deploys frontend assets to the primary bucket (with CloudFront cache invalidation).
- Deploys frontend assets to the backup bucket.
- CloudWatch log groups for both deployment operations.