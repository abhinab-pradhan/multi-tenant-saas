from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
from bson.errors import InvalidId
import jwt

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import db
from app.core.security import decode_access_token

bearer_scheme=HTTPBearer()
oauth2_scheme= OAuth2PasswordBearer(tokenUrl="/login")
    

async def get_current_user(credentials: HTTPAuthorizationCredentials=Depends(bearer_scheme)):

    token=credentials.credentials

    try:
        payload= decode_access_token(token)
        user_id= payload.get("sub")
        tenant_id= payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code= 401, 
                detail="invalid token"
                )

        current_user= await db.users.find_one({
            "_id":ObjectId(user_id),
            "tenant_id":ObjectId(tenant_id)
        })

        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="user not found"
            )

        return current_user

    except (jwt.InvalidTokenError, InvalidId, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="invalid or expired token"
        )
        
        
