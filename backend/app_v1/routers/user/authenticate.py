"""
This is the /user router

It contains the endpoints:
- POST /user/authenticate: logs the user in and returns a JWT token
"""

from app_v1.helpers.cognito_auth import Authenticate, createHash, verifyCognitoToken
from fastapi import Request, APIRouter, Depends, HTTPException, Body
import os, logging, jwt

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])

@router.post("/authenticate")
def cognito_initiate_authentication(
    request: Request,
    auth: Authenticate = Body(...)
):
    try:
        logger.info(f"Authenticating user {auth}")
        response = request.app.state.cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": auth.username,
                "PASSWORD": auth.password,
                "SECRET_HASH": createHash(COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET, auth.username)
            },
            ClientId=COGNITO_CLIENT_ID  # match register
        )
        tokens = response["AuthenticationResult"]
        decoded_user_data = verifyCognitoToken(request.app.state.cognito, tokens["AccessToken"])
        logger.info(f"User {auth.username} authenticated successfully.")
        logger.info(f"Decoded user data: {decoded_user_data}")
        
        return {
            "AccessToken": tokens["AccessToken"],
            "ExpiresIn": tokens["ExpiresIn"],
            "TokenType": tokens["TokenType"],
            "IdToken": tokens["IdToken"]
        }
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        raise HTTPException(status_code=400, detail=str(e))