"""
This is the /user router

It contains the endpoints:
- POST /user/change_subscription: Changes the current user's subscriptionLevel 
"""

from app_v1.helpers.cognito_auth import Authenticate, authenticateSession, createHash, verifyCognitoToken
from app_v1.helpers.rate_limits import getValidSubscriptionLevels
from fastapi import Request, APIRouter, Depends, HTTPException
import os, logging, jwt

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])

@router.get("/change_subscription")
def cognito_change_subscription_level(
    request: Request,
    subscription_level: str,
    user_data = Depends(authenticateSession)
):
    valid_subscription_levels = getValidSubscriptionLevels(request.app)
    if not subscription_level in valid_subscription_levels:
        logger.error(f"Invalid subscription level provided: {subscription_level}")
        raise HTTPException(status_code=400, detail=f"Subscription level '{subscription_level}' is invalid. Valid levels are: {', '.join(valid_subscription_levels)}")

    try:
        response = request.app.state.cognito.update_user_attributes(
            UserAttributes=[
                {
                    'Name': 'custom:subscriptionLevel',
                    'Value': subscription_level
                },
            ],
            AccessToken=user_data["AccessToken"]
        )
        return response
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        raise HTTPException(status_code=400, detail=str(e))