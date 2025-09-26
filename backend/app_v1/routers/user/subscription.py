"""
This is the /user router

It contains the endpoints:
- POST /user/change_subscription: Changes the current user's subscriptionLevel 
"""

from app_v1.helpers.cognito_auth import Authenticate, authenticateSession
from app_v1.helpers.rate_limits import getSubscription
from fastapi import Request, APIRouter, Depends, HTTPException
import os, logging, jwt

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])

@router.get("/subscription")
def user_get_current_subscription(
    request: Request,
    user_data = Depends(authenticateSession)
):
    try:
        for attr in user_data['UserAttributes']:
            if attr['Name'] == "custom:subscriptionLevel":
                return getSubscription(request.app, attr['Value'])
        raise Exception("No UserAttribute custom:subscriptionLevel")
    except Exception as e:
        logger.error(f"Error getting user's subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))