from fastapi import FastAPI, File, Query, HTTPException
import os, openai, boto3

EMBEDDER_URL = os.getenv("EMBEDDER_URL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")

app = FastAPI(title="Mart - RAG & LLM Powered Cover Letter Generator")

from pyapp.routers.generate_cover_letter import router as generate_cover_letter_router
from pyapp.routers.index_resume import router as index_resume_router
from pyapp.routers.user import router as user_router

app.include_router(index_resume_router)
app.include_router(generate_cover_letter_router)
app.include_router(user_router)

@app.on_event("startup")
async def initialise():
    print("Starting app...")

    print("Setting up OpenAI client for Embedder connection...")
    embedder = openai.OpenAI(   
        base_url = EMBEDDER_URL,
        api_key = "docker"
    )

    print("Setting up S3 client for resume storage...")
    try:
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=S3_BUCKET_NAME, CreateBucketConfiguration={'LocationConstraint': S3_REGION})
    except s3.exceptions.BucketAlreadyExists:
        print("Bucket already exists, continuing...")
    except Exception as e:
        print(f"WARNING:\tFailed to setup S3: {e}")

    print("Setting up app.state...")
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

    print("Startup complete.")
