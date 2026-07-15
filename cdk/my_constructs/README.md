# Python CDK Constructs for AWS Services

This directory contains Python CDK constructs for the PortfolioWebsite infrastructure.

## Table of Contents

- [AcmCertificate](#acmcertificate)
- [CloudFrontDistribution](#cloudfrontdistribution)
- [HostedZone](#hostedzone)
- [S3Bucket](#s3bucket)
- [SSMParameterReplicator](#ssmparameterreplicator)
- [SSMReplication](#ssmreplication)

## AcmCertificate

Creates a public ACM certificate for a given domain name with DNS validation and Certificate Transparency logging enabled. The certificate includes `www.<domain>` as a subject alternative name.

### Parameters

- `domain_name`: The primary domain name for the certificate.
- `hosted_zone`: The Route53 hosted zone used for DNS validation.

### Features

- Creates an ACM certificate with DNS validation.
- Includes `www.<domain>` as a subject alternative name.
- Enables Certificate Transparency logging.

## CloudFrontDistribution

Creates a CloudFront distribution backed by an S3 origin group with automatic failover to a backup bucket.

### Parameters

- `domain_name`: The primary domain name for the distribution.
- `certificate`: The ACM certificate (`ICertificate`).
- `website_s3_bucket`: The primary S3 bucket (`IBucket`).
- `backup_bucket_name`: Name of the S3 bucket used as the failover origin.
- `geo_restrictions` _(optional)_: Dict with `restriction_type` (`none`, `blacklist`, or `whitelist`) and `locations` (list of ISO 3166-1 country codes).
- `price_class` _(optional)_: CloudFront price class name. Defaults to `PRICE_CLASS_100`.

### Features

- S3 origin group with OAC-secured primary and fallback origins.
- Automatic failover on 5xx errors.
- Custom cache policy (30-day default TTL, Brotli/GZIP compression).
- Security response headers policy (CSP, HSTS, X-Frame-Options, XSS protection, Referrer-Policy).
- CloudFront Function for URL rewriting (e.g., `/resume` → `/resume.pdf`).
- Configurable geographic restrictions.

## HostedZone

Provides a helper function `lookup_hosted_zone` that looks up an existing Route53 hosted zone by domain name.

## S3Bucket

Creates a secure, versioned S3 bucket for static website content.

### Features

- S3-managed server-side encryption.
- Versioning enabled with noncurrent version expiration lifecycle rule.
- All public access blocked.
- Bucket policy denying non-TLS (HTTP) access.

## SSMParameterReplicator

Replicates SSM parameters from a source region to a target region using a Lambda-backed CloudFormation custom resource.

### Parameters

- `source_region`: AWS region to read parameters from.
- `target_region`: AWS region to write parameters to.
- `parameters`: List of `{source, target}` dicts mapping source parameter names to target names.
- `param_path_prefix` _(optional)_: SSM path prefix used to scope IAM permissions.
- `update_triggers` _(optional)_: List of values whose changes should trigger re-replication.

### Features

- Least-privilege IAM permissions scoped to the parameter path prefix.
- CloudWatch log group for Lambda execution logs.
- Re-runs replication on stack updates when `update_triggers` values change.

## SSMReplication

Provides the `build_ssm_replication_config` helper that derives a consistent `SsmReplicationConfig` (path prefix + parameter mappings) from a list of parameter names. Used by stacks to build the input for `SSMParameterReplicator`.