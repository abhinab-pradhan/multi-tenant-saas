
from fastapi import APIRouter, Depends, HTTPException

from app.database import db
from app.dependencies.auth import get_current_user
from app.schemas.role import RoleCreate

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("/")
async def create_role(
    role: RoleCreate,
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]

    existing = await db.roles.find_one({
        "name": role.name,
        "tenant_id": tenant_id
    })

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Role already exists for this tenant"
        )

    role_data = {
        "name": role.name,
        "description": role.description,
        "tenant_id": tenant_id,
        "permission_ids": []
    }

    result = await db.roles.insert_one(role_data)

    return {
        "message": "Role created successfully",
        "role_id": str(result.inserted_id),
        "name": role.name,
        "permission_ids": []
    }


@router.get("/")
async def list_roles(
    current_user: dict = Depends(get_current_user)
):
    roles = await db.roles.find({
        "tenant_id": current_user["tenant_id"]
    }).to_list(length=100)

    return [
        {
            "role_id": str(role["_id"]),
            "name": role["name"],
            "description": role["description"],
            "permission_ids": [
                str(permission_id)
                for permission_id in role["permission_ids"]
            ]
        }
        for role in roles
    ]
