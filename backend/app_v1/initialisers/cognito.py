import logging, boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialiseCognito(app):
    logger.info("Setting up Cognito client for user authentication...")
    try:
        app.state.cognito = boto3.client("cognito-idp", region_name="ap-southeast-2")
    except Exception as e:
        logger.error(f"Failed to initialize Cognito client: {e}")
        return False
    return True
