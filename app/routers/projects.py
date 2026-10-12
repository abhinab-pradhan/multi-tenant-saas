from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.database import db
from app.dependencies.auth import get_current_user
from app.schemas.project import ProjectCreate
from app.dependencies.permissions import require_permission
from app.schemas.project import ProjectCreate, ProjectUpdate

router=APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/")
async def create_project(project: ProjectCreate, current_user:dict = Depends(require_permission("project:create"))):
    project_data={
        "name":project.name,
        "description":project.description,
        "tenant_id":current_user["tenant_id"],
        "created_by":current_user["_id"]
    }

    result= await db.projects.insert_one(project_data)

    return{
        "message":"project created",

        "project_id":str(result.inserted_id),
        "name":project.name
    }

@router.get("/")
async def get_projects(current_user: dict = Depends(require_permission("project:read"))):
    projects= await db.projects.find({
        "tenant_id":current_user["tenant_id"]
    }).to_list(length=100)

    for project in projects:
        project["_id"]= str(project["_id"])
        project["tenant_id"]= str(project["tenant_id"])
        project["created_by"]= str(project["created_by"])

    return projects


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict=Depends(require_permission("project:read"))
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(
            status_code=400,
            detail="invalid project id"
        )

    project= await db.projects.find_one({
        "_id": ObjectId(project_id),
        "tenant_id": current_user["tenant_id"]
    })

    if not project:
        raise HTTPException(
            status_code=404,
            detail="project not found"
        )

    project["_id"]= str(project["_id"])
    project["tenant_id"]= str(project["tenant_id"])
    project["created_by"]= str(project["created_by"])

    return project

@router.put("/{project_id}")
async def update_project(
    project_id: str,
    project: ProjectUpdate,
    current_user: dict = Depends(
        require_permission("project:update")
    )
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID"
        )

    update_data = project.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    result = await db.projects.update_one(
        {
            "_id": ObjectId(project_id),
            "tenant_id": current_user["tenant_id"]
        },
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return {"message": "Project updated successfully"}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(
        require_permission("project:delete")
    )
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID"
        )

    result = await db.projects.delete_one({
        "_id": ObjectId(project_id),
        "tenant_id": current_user["tenant_id"]
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return {"message": "Project deleted successfully"}