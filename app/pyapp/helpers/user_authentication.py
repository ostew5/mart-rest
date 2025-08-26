from fastapi import FastAPI, Request, HTTPException, Depends
from datetime import datetime, timedelta
import jwt, os, json

JWT_SECRET = os.getenv("JWT_SECRET", "demo-secret")

def authenticate(
    request: Request
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
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
        JWT_SECRET, 
        algorithm="HS256"
    )

def rate_limiter(request_type: str):
    if request_type not in ["index_resume", "cover_letter"]:
        raise HTTPException(status_code=500, detail="Invalid request_type for rate_limiter")

    def _rate_limit(
        request: Request,
        user: dict = Depends(authenticate),
    ):
        now = datetime.utcnow()

        requests_list = request.app.state.users[user["uuid"]]["requests"].get(request_type, [])

        if not isinstance(requests_list, list):
            requests_list = []

        requests_list = [r for r in requests_list if r > now]

        try:
            with open("pyapp/helpers/rate-limits.json", "r") as f:
                rate_limits = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Couldn't get rate limits due to Exception: {e}")

        limit = rate_limits[request_type][user["subscription_level"]]

        if len(requests_list) >= limit:
            raise HTTPException(status_code=403, detail=f"You have exceeded your subscription level request limit for {request_type} requests")

        requests_list.append(datetime.utcnow() + timedelta(hours=1))
        request.app.state.users[user["uuid"]]["requests"][request_type] = requests_list

        return None

    return _rate_limit