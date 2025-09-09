"""
This is the /user POST endpoint for indexing applicant 
resumes and storing them in a S3 bucket.

It contains the endpoints:
- POST /user/login: logs the user in and returns a JWT token
"""

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, BackgroundTasks, Request
from app_v1.helpers.user_authentication import generate_jwt
from pydantic import BaseModel

router = APIRouter(prefix="/v1/user", tags=["user"])

class Login(BaseModel):
    uuid: str
    passkey: str

@router.post(
    "/login",
    summary="User login and JWT token generation",
    description="""
Authenticate a user and issue a JWT token.

**What it does**
- Looks up the user in `app.state.users` using the provided `uuid`.
- Verifies the `passkey` against the stored value.
- If valid, generates and returns a JWT token for the user.

**Request body**
- `uuid` *(str, required)* — The user's unique identifier.
- `passkey` *(str, required)* — The user's authentication secret.

**Responses**
- `200 OK` — Returns `{"token": "<jwt-token>"}` on successful authentication.
- `401 Unauthorized` — If the user is not found or the `passkey` is invalid.
"""
)
def login(
    login: Login,
    request: Request
):
    try:
        user = request.app.state.users[login.uuid]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"User not found with exception: {e}")

    if not user["passkey"] == login.passkey:
        raise HTTPException(status_code=401, detail=f"Failed to authenticate user")

    return {"token": generate_jwt(login.uuid)}