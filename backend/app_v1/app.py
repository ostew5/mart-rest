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

@app.on_event("startup")
async def initialise():
    logger.info("Starting app...")

    # Initialise all services
    logger.info("Initialising services...")
    from app_v1.initialisers.ollama import initialiseOllama
    from app_v1.initialisers.openai_client import initialiseOpenAI
    from app_v1.initialisers.s3 import initialiseS3
    from app_v1.initialisers.cognito import initialiseCognito
    from app_v1.initialisers.gemini import initialiseGemini
    from app_v1.initialisers.postgresql import initialisePostgreSQL

    for initialiser in [
        initialiseOllama,
        initialiseOpenAI,
        initialiseS3,
        initialiseCognito,
        initialiseGemini,
        initialisePostgreSQL
    ]:
        if not initialiser(app):
            raise Exception("Failed to initialize all services, check logs for details.")

    # Add all routers
    logger.info("Adding routers...")
    from app_v1.routers.generate_cover_letter.result import router as cover_letter_result_router
    from app_v1.routers.generate_cover_letter.start import router as cover_letter_start_router
    from app_v1.routers.generate_cover_letter.status import router as cover_letter_status_router
    from app_v1.routers.index_resume.start import router as index_resume_start_router
    from app_v1.routers.index_resume.status import router as index_resume_status_router
    from app_v1.routers.user.authenticate import router as user_authenticate_router
    from app_v1.routers.user.register import router as user_register_router
    from app_v1.routers.user.confirm import router as user_confirm_router
    from app_v1.routers.user.change_subscription import router as user_change_subscription_router
    from app_v1.routers.user.subscription import router as user_subscription_router

    for router in [
        cover_letter_result_router,
        cover_letter_start_router,
        cover_letter_status_router,
        index_resume_start_router,
        index_resume_status_router,
        user_authenticate_router,
        user_register_router,
        user_confirm_router,
        user_change_subscription_router,
        user_subscription_router
    ]:
        app.include_router(router)

    logger.info("Setting up app.state...")
    app.state.index_jobs = {}
    app.state.cover_letter_jobs = {}

    logger.info("Startup complete.")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down app...")

    # Shutdown all services
    from app_v1.shutdown.postgresql import shutdownPostgreSQL

    for shutdown in [
        shutdownPostgreSQL
    ]:
        if not shutdown(app):
            raise Exception("Failed to shutdown all services, check logs for details.")

    logger.info("Shutdown complete.")