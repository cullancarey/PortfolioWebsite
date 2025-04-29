from aws_cdk import Stack
from constructs import Construct
from my_constructs.s3_bucket import S3Bucket


class BackupWebsiteBucket(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.backup_website_bucket = S3Bucket(self, "BackupWebsiteBucket")

        # Expose bucket_name and bucket_arn for use in app.py
        self.bucket_name = self.backup_website_bucket.bucket.bucket_name
        self.bucket_arn = self.backup_website_bucket.bucket.bucket_arn
