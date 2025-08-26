"""
This is the /user POST endpoint for indexing applicant 
resumes and storing them in a S3 bucket.

It contains the endpoints:
- POST /user/login: logs the user in and returns a JWT token
"""

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, BackgroundTasks, Request
from pyapp.helpers.user_authentication import generate_jwt

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/user/login")
def login(
    uuid: str,
    passkey: str,
    request: Request
):
    try:
        user = request.app.state.users[uuid]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"User not found with exception: {e}")

    if not user["passkey"] == passkey:
        raise HTTPException(status_code=401, detail=f"Failed to authenticate user")

    return {"token": generate_jwt(uuid)}