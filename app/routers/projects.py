from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.database import db
from app.dependencies.auth import get_current_user
from app.schemas.project import ProjectCreate

router=APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/")
async def create_project(project: ProjectCreate, current_user:dict = Depends(get_current_user)):
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
async def get_projects(current_user: dict = Depends(get_current_user)):
    projects= await db.projects.find({
        "tenant_id":current_user["tenant_id"]
    }).to_list(length=100)

    return [
        {
            "project_id":str(project["_id"]),
            "name":project["name"],
            "description": project["description"]
        }
        for project in projects
        ]

@router.get("/{project_id}")
async def get_project(project_id:str, current_user: dict=Depends(get_current_user)):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(
            status_code=400,
            detail="invalid project id"
        )

    project=await db.projects.find_one({
        "_id":ObjectId(project_id),
        "tenant_id":current_user["tenant_id"]
    })

    if not project:
        raise HTTPException(
            status_code=404,
            detail="proect not found"
        )

    return{
        "project_id": str(project["_id"]),
        "name":project["name"],
        "description":project["description"]
    }