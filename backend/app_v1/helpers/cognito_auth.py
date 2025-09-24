import hmac, hashlib, base64
from pydantic import BaseModel
from fastapi import Request, HTTPException
import os, logging

COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Authenticate(BaseModel):
    username: str
    password: str
    email: str

async def get_authenticate(request: Request) -> Authenticate:
    content_type = request.headers.get("Content-Type", "")
    if 'application/json' in content_type: # Parse JSON data
        try:
            body = await request.json()
            return Authenticate(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif 'multipart/form-data' in content_type: # Parse form data
        form_data = await request.form()
        return Authenticate(username=form_data['username'], password=form_data['password'], email=form_data['email'])
    else:
        raise HTTPException(status_code=400, detail="Unsupported Content-Type")

def create_hash(clientId, clientSecret, username):
    message = bytes(username + clientId,'utf-8') 
    key = bytes(clientSecret,'utf-8') 
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode() 

def verify_cognito_token(cognito_client, access_token):
    try:
        # Verify the token using Cognito's built-in method
        response = cognito_client.get_user(
            AccessToken=access_token
        )
        
        # If successful, return user attributes or response data
        return response

    except cognito_client.exceptions.NotAuthorizedException as e:
        logger.error(f"Token is not authorized: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized")
    except Exception as e:
        logger.error(f"An error occurred while verifying the token: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def authenticate_session(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        user_data = verify_cognito_token(request.app.state.cognito, token)
        return user_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to authenticate user: {e}")