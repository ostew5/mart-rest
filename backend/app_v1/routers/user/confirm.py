"""
This is the /user router

It contains the endpoints:
- POST /user/confirm: 
"""

from app_v1.helpers.cognito_auth import Authenticate, createHash
from fastapi import Request, APIRouter, Depends, HTTPException, Body
import os, logging

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])

@router.get("/confirm")
def cognito_confirm_sign_up(
    confirmation_code: str,
    request: Request,
    auth: Authenticate = Body(...)
):
    try:
        response = request.app.state.cognito.confirm_sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=auth.username,
            ConfirmationCode=confirmation_code,
            SecretHash=createHash(COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET, auth.username)
        )
        return response
    except Exception as e:
        logger.error(f"Error during confirmation: {e}")
        raise HTTPException(status_code=400, detail=str(e))