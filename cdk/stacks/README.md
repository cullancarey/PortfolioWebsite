# CDK Stacks

This directory contains the stack layer used by [cdk/app.py](../app.py).

## Stacks

### ACMCertificatesStack

File: [acm_certificates_stack.py](acm_certificates_stack.py)

Purpose:

- Creates an ACM certificate for the website domain.
- In preview mode, includes wildcard SAN support via the underlying construct.
- Publishes certificate ARN to SSM.
- Triggers cross-region SSM replication via [../my_constructs/ssm_param_replicator.py](../my_constructs/ssm_param_replicator.py).

Key inputs:

- `domain_name`
- `hosted_zone_domain_name`
- `env_region`
- `ssm_params`
- `environment`
- `replication_target_region`

### BackupWebsiteBucketStack

File: [backup_website_bucket.py](backup_website_bucket.py)

Purpose:

- Creates a backup/failover S3 bucket.
- Publishes bucket ARN, regional domain name, and bucket name to SSM.
- Triggers cross-region SSM replication for these parameters.
- Adds bucket policy permissions for CloudFront read access (account-scoped distribution ARN wildcard).

Key inputs:

- `ssm_params`
- `region`
- `replication_target_region`

### WebsiteStack

File: [website_stack.py](website_stack.py)

Purpose:

- Imports certificate and backup bucket data from SSM.
- Creates the primary website S3 bucket.
- Creates CloudFront distribution with failover origin group.
- Creates Route53 alias records.
- Deploys built frontend assets to primary and backup buckets.

Key inputs:

- `domain_name`
- `hosted_zone_domain_name`
- `source_file_path`
- `acm_ssm_params`
- `backup_website_bucket_ssm_params`
- `geo_restrictions`
- `cloudfront_price_class`
- `include_www_alias`

## Preview vs Non-Preview Behavior

Preview behavior is orchestrated in [../app.py](../app.py), not in these stacks directly.

- Preview deployments require `preview_id`.
- Preview stack IDs are suffixed for isolation.
- Preview SSM parameter paths are namespaced by `preview_id`.
- Preview website deployments disable the `www` Route53 alias (`include_www_alias=False`).