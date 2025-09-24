from fastapi import FastAPI
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mart - LLM & RAG Powered Cover Letter Generator",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json"
)

# Import routers
from app_v1.routers.generate_cover_letter.result import router as cover_letter_result_router
from app_v1.routers.generate_cover_letter.start import router as cover_letter_start_router
from app_v1.routers.generate_cover_letter.status import router as cover_letter_status_router

from app_v1.routers.index_resume.start import router as index_resume_start_router
from app_v1.routers.index_resume.status import router as index_resume_status_router

from app_v1.routers.user.authenticate import router as user_authenticate_router
from app_v1.routers.user.register import router as user_register_router
from app_v1.routers.user.confirm import router as user_confirm_router

# Add routers
app.include_router(cover_letter_result_router)
app.include_router(cover_letter_start_router)
app.include_router(cover_letter_status_router)

app.include_router(index_resume_start_router)
app.include_router(index_resume_status_router)

app.include_router(user_authenticate_router)
app.include_router(user_register_router)
app.include_router(user_confirm_router)

# Add initialisers
from app_v1.initialisers.ollama import initialiseOllama
from app_v1.initialisers.openai_client import initialiseOpenAI
from app_v1.initialisers.s3 import initialiseS3
from app_v1.initialisers.cognito import initialiseCognito
from app_v1.initialisers.gemini import initialiseGemini

@app.on_event("startup")
async def initialise():
    logger.info("Starting app...")

    # Initialise all services
    for initialiser in [
        initialiseOllama,
        initialiseOpenAI,
        initialiseS3,
        initialiseCognito,
        initialiseGemini
    ]:
        if not initialiser(app):
            raise Exception("Failed to initialize all services, check logs for details.")

    logger.info("Setting up app.state...")
    app.state.index_jobs = {}
    app.state.cover_letter_jobs = {}

    logger.info("Startup complete.")
