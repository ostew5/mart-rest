from fastapi import FastAPI, File, Query, HTTPException
import os, openai, boto3

EMBEDDER_URL = os.getenv("EMBEDDER_URL")

app = FastAPI(title="Mart 1.0 - Resume Generator")

from pyapp.routers.generate_cover_letter import router as generate_cover_letter_router
from pyapp.routers.index_resume import router as index_resume_router

app.include_router(index_resume_router)
app.include_router(generate_cover_letter_router)

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
        s3.create_bucket(Bucket="resume-storage-ostew5", CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-2'})
    except s3.exceptions.BucketAlreadyExists:
        print("Bucket already exists, continuing...")
    except Exception as e:
        print(f"WARNING:\tFailed to setup S3: {e}")

    print("Setting up app.state...")
    app.state.embedder = embedder
    app.state.s3 = s3
    app.state.index_jobs = {}
    app.state.cover_letter_jobs = {}

    print("Startup complete.")
