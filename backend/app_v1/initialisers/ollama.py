import logging, os, requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBEDDER_URL = os.getenv("EMBEDDER_URL")
EMBEDDER_ID = os.getenv("EMBEDDER_ID")

def initialiseOllama(app):
    logger.info(f"Pulling {EMBEDDER_ID} in Ollama...")
    try:
        response = requests.post(f"{EMBEDDER_URL}/api/pull", json={"model": EMBEDDER_ID}, stream=True)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    data = chunk.decode('utf-8').strip()
                    if data.startswith("{") and data.endswith("}"):
                        json_data = requests.compat.json.loads(data)
                except Exception as e:
                    logger.error(f"Error processing JSON: {e}")
    except requests.RequestException as e:
        logger.error(f"Failed to pull model: {e}")
        return False # return false if failed
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False # return false if failed

    logger.info(f"Verifying model {EMBEDDER_ID} is available...")
    try:
        response = requests.get(f"{EMBEDDER_URL}/api/tags")
        response.raise_for_status()
        tags = response.json()
        logger.info(f"Available tags in {EMBEDDER_URL}: {tags}")
        for model in tags.get("models", []):
            if model.get("name") == EMBEDDER_ID:
                logger.info(f"Found model {EMBEDDER_ID} in Ollama.")
                return True
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve tags: {e}")
        return False # return false if failed
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False # return false if failed
    return False