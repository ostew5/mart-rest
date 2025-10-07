import logging, os, boto3, sqs_extended_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQS_S3_BUCKET = os.getenv("SQS_S3_BUCKET")
SQS_REGION = os.getenv("SQS_REGION")
SQS_QUEUE = os.getenv("SQS_QUEUE")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

def initialiseSQS(app):
    logger.info("Setting up extended SQS client for handling job queue...")
    try:
        sqs_extended_client = boto3.client("sqs", region_name=SQS_REGION)
        sqs_extended_client.large_payload_support = SQS_S3_BUCKET
        sqs_extended_client.use_legacy_attribute = False
        app.state.sqs = sqs_extended_client

        app.state.sqs_queue = app.state.sqs.create_queue(
            QueueName = SQS_QUEUE
        )
        app.state.sqs_queue_url = app.state.sqs.get_queue_url(
            QueueName = SQS_QUEUE
        )[SQS_QUEUE_URL]

        app.state.sqs.s3_client.create_bucket(Bucket=app.state.sqs.large_payload_support)

    except Exception as e:
        logger.warning(f"Exception at SQS setup: {e}")
        return False
    return True
