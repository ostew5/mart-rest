import logging, os, requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_URL = os.getenv("GEMINI_API_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def initialiseGemini(app):
    logger.info("Testing Gemini connection...")

    headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}
    payload = {"contents": [{"parts": [{"text": "Hi"}]}]} # Single token input to test

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Gemini response code: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to connect to Gemini API: {e}")
        return False
    return True
