import logging, os, boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION", None)

def initialiseS3(app):
    logger.info("Setting up S3 client for storage...")
    try:
        s3 = boto3.client("s3")
        logger.info(f"Creating bucket with Bucket={S3_BUCKET_NAME} 'LocationConstraint': {S3_REGION}")
        if S3_REGION is None:
            s3.create_bucket(Bucket=S3_BUCKET_NAME)
        else:
            location_constraint = {'LocationConstraint': S3_REGION}
            s3.create_bucket(
                Bucket=S3_BUCKET_NAME,
                CreateBucketConfiguration=location_constraint
            )
    except s3.exceptions.BucketAlreadyExists:
        logger.info("Bucket already exists, continuing...")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        logger.info("Bucket already owned by you, continuing...")
    except Exception as e:
        logger.warning(f"Exception at S3 setup: {e}")
        return False
    app.state.s3 = s3
    return True
