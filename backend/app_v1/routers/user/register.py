"""
This is the /user router

It contains the endpoints:
- POST /user/register: 
"""

from app_v1.helpers.cognito_auth import Authenticate, get_authenticate, create_hash
from fastapi import Request, APIRouter, Depends, HTTPException
import logging, os

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])

@router.post("/register")
def cognito_sign_up(
    subscription_level: str = "Basic",
    request: Request,
    auth: Authenticate = Depends(get_authenticate)
):
    try:
        logger.info(f"Cognito ID: {COGNITO_CLIENT_ID}, Secret: {COGNITO_CLIENT_SECRET}")
        logger.info(f"Authenticating user {auth}")
        response = request.app.state.cognito.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=auth.username,
            Password=auth.password,
            SecretHash=create_hash(
                COGNITO_CLIENT_ID,
                COGNITO_CLIENT_SECRET,
                auth.username
            ),
            UserAttributes=[
                {
                    "Name": "email", 
                    "Value": auth.email
                },
                {
                    "Name": "subscriptionLevel", 
                    "Value": subscription_level
                }
            ]
        )
        return response
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(status_code=400, detail=str(e))