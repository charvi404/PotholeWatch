from dotenv import load_dotenv
import boto3, os
from botocore.config import Config

load_dotenv()  # ✅ Load the .env file

aws_config = Config(region_name=os.getenv("AWS_REGION", "ap-south-1"))
s3 = boto3.client(
    "s3",
    config=aws_config,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

try:
    result = s3.list_buckets()
    print("✅ Connected to AWS S3! Buckets:", [b["Name"] for b in result["Buckets"]])
except Exception as e:
    print("❌ S3 connection failed:", e)
