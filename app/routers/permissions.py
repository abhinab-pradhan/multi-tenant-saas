
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.database import db
from app.dependencies.auth import get_current_user
from app.schemas.permission import PermissionCreate

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.post("/")
async def create_permission(
    permission: PermissionCreate,
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]

    existing = await db.permissions.find_one({
        "name": permission.name,
        "tenant_id": tenant_id
    })

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Permission already exists for this tenant"
        )

    permission_data = {
        "name": permission.name,
        "description": permission.description,
        "tenant_id": tenant_id
    }

    result = await db.permissions.insert_one(permission_data)

    return {
        "message": "Permission created successfully",
        "permission_id": str(result.inserted_id),
        "name": permission.name
    }


@router.get("/")
async def list_permissions(
    current_user: dict = Depends(get_current_user)
):
    permissions = await db.permissions.find({
        "tenant_id": current_user["tenant_id"]
    }).to_list(length=100)

    return [
        {
            "permission_id": str(permission["_id"]),
            "name": permission["name"],
            "description": permission["description"]
        }
        for permission in permissions
    ]
