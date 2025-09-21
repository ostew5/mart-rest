from fastapi import FastAPI, File, Query, HTTPException
from pydantic import BaseModel
import os, openai, boto3
import logging, requests

EMBEDDER_URL = os.getenv("EMBEDDER_URL")
EMBEDDER_ID = os.getenv("EMBEDDER_ID")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mart - LLM & RAG Powered Cover Letter Generator",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json"
)

from app_v1.routers.cover_letter_result import router as cover_letter_result_router
from app_v1.routers.cover_letter_start import router as cover_letter_start_router
from app_v1.routers.cover_letter_status import router as cover_letter_status_router
from app_v1.routers.index_resume_start import router as index_resume_start_router
from app_v1.routers.index_resume_status import router as index_resume_status_router
from app_v1.routers.user import router as user_router

app.include_router(cover_letter_result_router)
app.include_router(cover_letter_start_router)
app.include_router(cover_letter_status_router)
app.include_router(index_resume_start_router)
app.include_router(index_resume_status_router)
app.include_router(user_router)

class PullModelRequest(BaseModel):
    model: str
    insecure: bool = False
    stream: bool = True

@app.on_event("startup")
async def initialise():
    logger.info("Starting app...")

    logger.info(f"Pulling {EMBEDDER_ID} in Ollama...")
    def handle_stream_response(response):
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    data = chunk.decode('utf-8').strip()
                    if data.startswith("{") and data.endswith("}"):
                        json_data = requests.compat.json.loads(data)
                except Exception as e:
                    logger.error(f"Error processing JSON: {e}")

    try:
        response = requests.post(f"{EMBEDDER_URL}/api/pull", json={"model": EMBEDDER_ID}, stream=True)
        response.raise_for_status()
        handle_stream_response(response)
    except requests.RequestException as e:
        logger.error(f"Failed to pull model: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize the application")

    logger.info(f"Verifying model {EMBEDDER_ID} is available...")
    try:
        response = requests.get(f"{EMBEDDER_URL}/api/tags")
        response.raise_for_status()
        tags = response.json()
        logger.info(f"Available tags in {EMBEDDER_URL}: {tags}")
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve tags: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize the application")

    logger.info("Setting up OpenAI client for Embedder connection...")
    embedder = openai.OpenAI(
        base_url=f"{EMBEDDER_URL}/v1/",
        api_key="docker"
    )

    logger.info("Testing embedder connection...")
    try:
        response = embedder.embeddings.create(
            input=["Hi"],
            model=EMBEDDER_ID
        )
        logger.info(f"Embedder response: {response}")
    except Exception as e:
        logger.error(f"Failed to connect to embedder: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize the application")

    logger.info("Testing Gemini connection...")
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    
    payload = {
        "contents": [
            {"parts": [{"text": "Hi"}]}
        ]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error: {e}")

    logger.info("Setting up S3 client for resume storage...")
    try:
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=S3_BUCKET_NAME, CreateBucketConfiguration={'LocationConstraint': S3_REGION})
    except s3.exceptions.BucketAlreadyExists:
        logger.info("Bucket already exists, continuing...")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        logger.info("Bucket already owned by you, continuing...")
    except Exception as e:
        logger.warning(f"Exception at S3 setup: {e}")

    logger.info("Setting up app.state...")
    app.state.embedder = embedder
    app.state.s3 = s3
    app.state.users = {
        "6c730f37-0cf6-4076-93ee-326546e8e748":{
            "passkey": "123456",
            "subscription_level": "basic",
            "requests": {
                "index_resume": [],
                "cover_letter": []
            }
        },
        "281d10f6-3bed-40c2-96f0-ba120f38ecbd":{
            "passkey": "secret",
            "subscription_level": "premium",
            "requests": {
                "index_resume": [],
                "cover_letter": []
            }
        }
    }
    app.state.index_jobs = {}
    app.state.cover_letter_jobs = {}

    logger.info("Startup complete.")
