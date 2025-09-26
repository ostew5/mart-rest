import hmac, hashlib, base64
from pydantic import BaseModel
from fastapi import Request, HTTPException, Form
import os, logging

COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Authenticate(BaseModel):
    username: str
    password: str
    email: str

def createHash(clientId, clientSecret, username):
    # This function creates a hash using HMAC-SHA256 for the given username, client ID, and client secret.
    message = bytes(username + clientId,'utf-8') 
    key = bytes(clientSecret,'utf-8') 
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode() 

def verifyCognitoToken(cognito_client, access_token):
    # This function verifies a Cognito access token using the provided Cognito client.
    try:
        # Calls the Cognito client's get_user method with the provided access token.
        response = cognito_client.get_user(
            AccessToken=access_token
        )
        
        # Returns the response containing user information if the token is valid.
        return response

    except cognito_client.exceptions.NotAuthorizedException as e:
        # Catches and handles NotAuthorizedException exceptions, logging an error message and raising a 401 Unauthorized exception.
        logger.error(f"Token is not authorized: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized")
    except Exception as e:
        # Catches and handles any other exceptions, logging an error message and raising a 500 Internal Server Error exception.
        logger.error(f"An error occurred while verifying the token: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def authenticateSession(request: Request):
    # This function authenticates a session by verifying a Cognito access token from the request's Authorization header.
    auth_header = request.headers.get("Authorization")
    # Checks if the Authorization header is missing or not in the correct format (Bearer token).
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    # Extracts the access token from the Authorization header.
    token = auth_header.split(" ")[1]
    try:
        # Calls verifyCognitoToken with the Cognito client and the extracted token to authenticate the user.
        user_data = verifyCognitoToken(request.app.state.cognito, token)
        user_data["AccessToken"] = token
        # Returns the user data if the token is valid.
        return user_data
    except Exception as e:
        # Catches any exceptions that may occur during the authentication process, logging an error message and raising a 401 Unauthorized exception.
        raise HTTPException(status_code=401, detail=f"Failed to authenticate user: {e}")