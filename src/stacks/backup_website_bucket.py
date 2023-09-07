from aws_cdk import Stack
from constructs import Construct
from my_constructs.s3_bucket import S3Bucket


class BackupWebsiteBucket(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.backup_website_bucket = S3Bucket(self, "BackupWebsiteBucket")
