import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, HTTPBearer

JWT_SECRET = os.environ["JWT_SECRET"]
API_KEY = os.environ["API_KEY"]
TOKEN_LIFETIME = timedelta(hours=8)


def create_token(account_id, role):
    expires = datetime.now(timezone.utc) + TOKEN_LIFETIME
    return jwt.encode({"sub": str(account_id), "role": role, "exp": expires}, JWT_SECRET, algorithm="HS256")


bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def current_account(credentials=Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, "Not logged in", headers={"WWW-Authenticate": "Bearer"})
    try:
        # decode also checks the signature and the expiry time.
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})


def require_admin(account=Depends(current_account)):
    if account["role"] != "admin":
        raise HTTPException(403, "Only admins can do this")
    return account


def require_api_key(api_key=Depends(api_key_header)):
    # compare_digest takes the same time however many characters match, so the key
    # can't be guessed one character at a time by measuring response times.
    if api_key is None or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(401, "Missing or invalid API key")
