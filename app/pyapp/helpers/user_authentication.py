from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, timedelta
import jwt

JWT_TOKEN = os.getenv("JWT_TOKEN")

def authenticate(
    request: Request
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        payload["subscription_level"] = request.app.state.users[payload["uuid"]]["subscription_level"]
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Exception hit: {e}")

def generate_jwt(uuid):
    expiration = datetime.utcnow() + timedelta(hours=1)
    issued_at = datetime.utcnow()

    return jwt.encode(
        {
            "uuid": uuid,
            "iat": issued_at,
            "exp": expiration
        },
        JWT_TOKEN, 
        algorithm="HS256"
    )

def rate_limit(
    request_type: str,
    user: dict = Depends(authenticate),
    app: FastAPI
):
    if not request_type in ["index_resume", "cover_letter"]:
        raise HTTPException(status_code=500, detail=f"Bad rate_limit() call, invalid request param")

    now = datetime.utcnow()
    requests = app.state.users[user["uuid"]]["requests"][request_type]

    requests = [r for r in requests if r > now]

    rate_limits = {}
    try:
        with open("pyapp/helpers/rate-limits.json", "r") as f:
            rate_limits = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Couldn't get rate limits")

    if len(requests) >= rate_limits[request_type][user["subscription_level"]]
        raise HTTPException(status_code=403, detail=f"You have exceeded your subscription level request limit for {request_type} requests")

    requests += datetime.utcnow() + timedelta(hours=1)

    app.state.users[user["uuid"]]["requests"][request_type] = requests

    return