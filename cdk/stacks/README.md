# Python CDK Stacks for AWS Services

This repository contains Python CDK stacks for various AWS services such as ACM, S3, CloudFront, and API Gateway.

## Table of Contents

- [ACMCertificates](#acmcertificates)
- [BackupWebsiteBucket](#backupwebsitebucket)
- [Website](#website)

## ACMCertificates

This stack creates ACM certificates for a given domain name and its subdomain (e.g., `form.domain.com`).

### Parameters

- `account_id`: AWS account ID.
- `domain_name`: The domain name for the certificates.

### Features

- Creates an ACM certificate for the main domain.
- Creates an ACM certificate for the `form` subdomain.
- Associates the certificates with a Route53 hosted zone.

## BackupWebsiteBucket

This stack creates an S3 bucket that serves as a backup for the website.

### Features

- Creates an S3 bucket with specific configurations.

## Website

This stack sets up the infrastructure for a website, including S3 buckets, CloudFront distributions, and API Gateway.

### Parameters

- `account_id`: AWS account ID.
- `region`: AWS region.
- `domain_name`: The domain name for the website.
- `source_file_path`: The path to the source files for the website.
- `environment`: The environment (e.g., dev, prod).
- `website_certificate`: The ACM certificate for the website.
- `contact_form_certificate`: The ACM certificate for the contact form.
- `backup_website_bucket`: The S3 bucket for the backup website.

### Features

- Creates an S3 bucket for the website.
- Sets up a CloudFront distribution for the website.
- Adds Route53 records for the main domain and `www` subdomain.
- Sets up an API Gateway and Lambda function for the contact form.
- Creates a CloudFront distribution for the contact form API.
- Adds a Route53 record for the `form` subdomain.
- Deploys website files to the S3 bucket.
- Deploys backup website files to the backup S3 bucket.