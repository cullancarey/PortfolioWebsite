# CDK Constructs

This directory contains reusable CDK constructs and helpers used by the stack layer.

## Construct Inventory

- [acm_certificate.py](acm_certificate.py)
- [cloudfront_distribution.py](cloudfront_distribution.py)
- [s3_bucket.py](s3_bucket.py)
- [ssm_param_replicator.py](ssm_param_replicator.py)

Helper modules:

- [hosted_zone.py](hosted_zone.py)
- [ssm_replication.py](ssm_replication.py)

## AcmCertificate

File: [acm_certificate.py](acm_certificate.py)

Creates an ACM certificate validated through Route53.

Notable behavior:

- Always includes `www.<domain>` as SAN.
- Optionally includes wildcard SAN (`*.<domain>`) via `include_wildcard_san=True` (used by preview infrastructure).
- Enables transparency logging.

## CloudFrontDistribution

File: [cloudfront_distribution.py](cloudfront_distribution.py)

Creates the CloudFront distribution used for the website.

Notable behavior:

- Uses Origin Access Control (OAC) for S3 origins.
- Uses origin group failover to a backup S3 bucket.
- Configures security headers and cache policy.
- Supports geo restrictions.
- Includes URL rewrite function for `/resume`.

## S3Bucket

File: [s3_bucket.py](s3_bucket.py)

Creates a hardened S3 bucket for website content.

Notable behavior includes secure defaults such as encryption, public access blocking, and bucket policy controls applied at stack level.

## SSMParameterReplicator

File: [ssm_param_replicator.py](ssm_param_replicator.py)

Replicates selected SSM parameters from source region to target region using a Docker Lambda and CloudFormation custom resource provider.

Notable behavior:

- Least-privilege IAM path scoping.
- Custom resource properties include source/target/parameter list so updates trigger re-execution.

## Helpers

### hosted_zone.py

Provides `lookup_hosted_zone(...)` returning `route53.IHostedZone` using Route53 lookup.

### ssm_replication.py

Builds replication path metadata consumed by [ssm_param_replicator.py](ssm_param_replicator.py).