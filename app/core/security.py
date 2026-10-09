import os
import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from dotenv import load_dotenv

load_dotenv()

password_hash=PasswordHash.recommended()

JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES","30"))


def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(password:str,hashed_password:str) -> bool:
    return password_hash.verify(password,hashed_password)

def create_access_token(user_id:str, tenant_id: str) -> str:
    expire_at =datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload={
        "sub":user_id,
        "tenant_id":tenant_id,
        "algorithm":JWT_ALGORITHM
    }

    return jwt.encode(
        payload,JWT_SECRET_KEY,algorithm=JWT_ALGORITHM
    )

def decode_access_token(token:str) -> dict:
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM]
    )