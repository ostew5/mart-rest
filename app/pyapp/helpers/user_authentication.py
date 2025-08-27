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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to authenticate user: {e}")

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

def get_subscription_limits():
    try:
        with open("pyapp/helpers/subscription-limits.json", "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Couldn't get rate limits due to Exception: {e}")

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

        limit = get_subscription_limits()["requests_per_hour"][request_type][user["subscription_level"]]

        if len(requests_list) >= limit:
            raise HTTPException(status_code=403, detail=f"You have exceeded your subscription level request limit for {request_type} requests")

        _1hour = datetime.utcnow() + timedelta(hours=1)

        requests_list.append(_1hour)

        request.app.state.users[user["uuid"]]["requests"][request_type] = requests_list

        return lambda success : tick_rate_limiter(request.app, user, request_type, _1hour, success)

    return _rate_limit

def tick_rate_limiter(
    app: FastAPI,
    user: dict,
    request_type: dict,
    _1hour,
    success: bool
):
    if not success:
        return app.state.users[user["uuid"]]["requests"][request_type].remove(_1hour)
    return None