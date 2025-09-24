import logging, os, openai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBEDDER_URL = os.getenv("EMBEDDER_URL")
EMBEDDER_ID = os.getenv("EMBEDDER_ID")

def initialiseOpenAI(app):
    logger.info("Setting up OpenAI client for Embedder connection...")
    try:
        app.state.embedder = openai.OpenAI(
            base_url=f"{EMBEDDER_URL}/v1/",
            api_key="docker"
        )
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return False
        
    logger.info("Testing OpenAI Client embedder connection...")
    try:
        response = app.state.embedder.embeddings.create(
            input=["Hi"],
            model=EMBEDDER_ID
        )
        logger.info(f"Embedder response: {response}")
    except Exception as e:
        logger.error(f"Failed to connect to embedder: {e}")
        return False
    return True
