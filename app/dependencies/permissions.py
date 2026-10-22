from fastapi import Depends, HTTPException
from bson import ObjectId

from app.database import db
from app.dependencies.auth import get_current_user

def require_permission(permission_name: str):
    async def permission_checker(
            current_user: dict=Depends(get_current_user)
    ):
        tenant_id= current_user["tenant_id"]
        role_ids= current_user.get("role_ids",[])

        if not role_ids:
            raise HTTPException(
                status_code=403,
                detail="no roles assigned to this user"
            )

        roles= await db.roles.find({
            "_id": {"$in": role_ids},
            "tenant_id": tenant_id
        }).to_list(length=100)

        permission_ids=set()

        for role in roles:
            permission_ids.update(role.get("permission_ids", []))

        if not permission_ids:
            raise HTTPException(
                status_code=403,
                detail="no permission assigned ot this user"
            )

        permission= await db.permissions.find_one({
            "_id":{"$in": list(permission_ids)},
            "tenant_id": tenant_id,
            "name": permission_name
        })

        if not permission:
            raise HTTPException(
                status_code=403,
                detail=f"permission required: {permission_name}"
            )

        return current_user

    return permission_checker
require_project_read=require_permission("project:read")
require_user_manage= require_permission("user:manage")