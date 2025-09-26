"""
This is the /user router

It contains the endpoints:
- POST /user/register: 
"""

from app_v1.helpers.cognito_auth import Authenticate, createHash
from app_v1.helpers.rate_limits import getValidSubscriptionLevels
from fastapi import Request, APIRouter, Depends, HTTPException, Body
import logging, os

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])

@router.post("/register")
def cognito_sign_up(
    request: Request,
    auth: Authenticate = Body(...),
    subscription_level: str = "Basic"
):  
    valid_subscription_levels = getValidSubscriptionLevels(request.app)
    if not subscription_level in valid_subscription_levels:
        logger.error(f"Invalid subscription level provided: {subscription_level}")
        raise HTTPException(status_code=400, detail=f"Subscription level '{subscription_level}' is invalid. Valid levels are: {', '.join(valid_subscription_levels)}")

    try:
        logger.info(f"Cognito ID: {COGNITO_CLIENT_ID}, Secret: {COGNITO_CLIENT_SECRET}")
        logger.info(f"Authenticating user {auth}")
        response = request.app.state.cognito.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=auth.username,
            Password=auth.password,
            SecretHash=createHash(
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
                    "Name": "custom:subscriptionLevel", 
                    "Value": subscription_level
                }
            ]
        )
        return response
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(status_code=400, detail=str(e))