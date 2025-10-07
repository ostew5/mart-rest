import logging, os, boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQS_S3_BUCKET = os.getenv("SQS_S3_BUCKET")
SQS_REGION = os.getenv("SQS_REGION")
SQS_QUEUE = os.getenv("SQS_QUEUE")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

def process_job(payload):
    """Do your heavy lifting here."""
    # Dummy processing
    time.sleep(2)  # pretend we did something
    result = {'message': f"Processed {payload['payload']}"}
    return result

def poll_queue(app):
    while True:
        response = app.state.sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,          # long polling
            VisibilityTimeout=30,        # seconds the message is hidden from other workers
            MessageAttributeNames=['All']
        )

        messages = response.get('Messages', [])
        if not messages:
            continue

        for msg in messages:
            receipt_handle = msg['ReceiptHandle']
            body = json.loads(msg['Body'])
            job_id = body['job_id']

            logger.info(f"Processing job {job_id}")

            # Mark processing
            job_status[job_id] = {'status': 'processing'}

            # Do the work
            try:
                result = process_job(body)
                job_status[job_id] = {'status': 'done', 'result': result}
            except Exception as e:
                logger.exception(f"Job {job_id} failed: {e}")
                # Optionally requeue or let it go to DLQ by not deleting

            # Delete the message (only after success)
            app.state.sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"Job {job_id} completed")

if __name__ == '__main__':
    app.state = {}

    from worker.initialisers.ollama import initialiseOllama
    from worker.initialisers.s3 import initialiseS3
    from worker.initialisers.postgresql import initialisePostgreSQL

    for initialiser in [
        initialiseOllama,
        initialiseS3,
        initialisePostgreSQL
    ]:
        if not initialiser(app):
            raise Exception("Failed to initialize all services, check logs for details.")

    poll_queue(app)