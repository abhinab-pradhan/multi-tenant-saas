
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from bson.errors import InvalidId

from app.database import db
from app.dependencies.auth import get_current_user
from app.schemas.role import RoleCreate
from app.schemas.role import RoleCreate, RolePermissionAssign

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


@router.post("/{role_id}/permissions")
async def assign_permissions(
    role_id: str,
    assignment: RolePermissionAssign,
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]

    # Validate the role ID
    if not ObjectId.is_valid(role_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid role ID"
        )

    role = await db.roles.find_one({
        "_id": ObjectId(role_id),
        "tenant_id": tenant_id
    })

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    # Validate and convert permission IDs
    if any(not ObjectId.is_valid(pid) for pid in assignment.permission_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more permission IDs are invalid"
        )

    permission_ids = list({
        ObjectId(pid) for pid in assignment.permission_ids
    })

    # Ensure every permission belongs to this tenant
    permissions = await db.permissions.find({
        "_id": {"$in": permission_ids},
        "tenant_id": tenant_id
    }).to_list(length=len(permission_ids))

    if len(permissions) != len(permission_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more permissions do not exist in this tenant"
        )

    # Add permissions without removing existing assignments
    await db.roles.update_one(
        {
            "_id": role["_id"],
            "tenant_id": tenant_id
        },
        {
            "$addToSet": {
                "permission_ids": {"$each": permission_ids}
            }
        }
    )

    return {
        "message": "Permissions assigned successfully",
        "role_id": role_id,
        "permission_ids": [str(pid) for pid in permission_ids]
    }
