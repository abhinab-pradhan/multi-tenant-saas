from fastapi import FastAPI, HTTPException, Depends
from bson import ObjectId

from app.database import client,db
from app.schemas.tenant import TenantCreate
from app.schemas.user import UserCreate, UserLogin
from app.core.security import hash_password, verify_password, create_access_token
from app.dependencies.auth import get_current_user
from app.routers.projects import router as projects_router
from app.routers.permissions import router as permissions_router
from app.routers.roles import router as roles_router
from app.schemas.user import UserRoleAssign
from bson.errors import InvalidId
from app.dependencies.permissions import require_permission
from app.database import create_indexes

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app:FastAPI):
    await create_indexes()
    yield

app=FastAPI(
    title="Multi-Tenant SaaS API",
    version="1.0",
    lifespan=lifespan
)

app.include_router(projects_router)
app.include_router(permissions_router)
app.include_router(roles_router)

@app.get("/")
async def root():
    return{
        "message":"Multi-Tenant SaaS API is running"
    }

@app.get("/health")
async def health_check():
    try:
        await client.admin.command("ping")

        return{
            "status":"healthy",
            "database":"MongoDB connected"
        }

    except Exception as e:
        return{
            "status":"unhealthy",
            "database":"MongoDB connection failed",
            "error":str(e)
        }

@app.post("/tenants")
async def create_tenant(tenant:TenantCreate):

    tenant_data={
        "name":tenant.name
    }

    result= await db.tenants.insert_one(tenant_data)

    return{
        "message":"tenant created successfully",
        "tenant_id":str(result.inserted_id),
        "name":tenant.name
    }

@app.post("/users")
async def create_user(user:UserCreate):

    user_data={
        "email": user.email,
        "password_hash":hash_password(user.password),
        "tenant_id":ObjectId(user.tenant_id),
        "role_ids":[]
    }

    result=await db.users.insert_one(user_data)

    return{
        "message":"user created successfully",
        "user_id":str(result.inserted_id),
        "tenant_id":user.tenant_id
    }


'''
@app.get("/test")
async def test():
    hashed=hash_password("pass123")
    return{
        "hashed":hashed
    }
'''

@app.post("/login")
async def login(user:UserLogin):
    #find user by email
    existing_user= await db.users.find_one({
        "email":user.email
    })

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="invalid email or password"
        )

    #verify the submitted password against the stored hash
    if not verify_password(user.password,existing_user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="invalid email or password"
        )

    #generate a jwt for this authenticated user
    access_token= create_access_token(
        user_id=str(existing_user["_id"]),
        tenant_id=str(existing_user["tenant_id"])
    )

    return {
        "access_token": access_token,
        "token_type":"bearer"
    }

@app.get("/me")
async def get_profile(current_user:dict=Depends(get_current_user)):
    return{
        "user_id": str(current_user["_id"]),
        "email": current_user["email"],
        "tenant_id": str(current_user["tenant_id"])
    }

@app.post("/users/{user_id}/roles")
async def assign_roles_to_user(user_id: str, assignment: UserRoleAssign, current_user: dict=Depends(get_current_user)):
    tenant_id= current_user["tenant_id"]

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400,
            detail="invalid user id"
        )

    target_user= await db.users.find_one({
        "_id": ObjectId(user_id),
        "tenant_id":tenant_id
    })

    if not target_user:
        raise HTTPException(
            status_code=400,
            detail="one or more role ids are invalid"
        )

    role_ids= list({ObjectId(rid) for rid in assignment.role_ids})

    roles= await db.roles.find({
        "_id":{"$in": role_ids},
        "tenant_id": tenant_id
    }).to_list(length=len(role_ids))

    if len(roles) != len(role_ids):
        raise HTTPException(
            status_code=400,
            detail="one or more roles do not exist in this tenant"
        )

    await db.users.update_one(
        {
            "_id": target_user["_id"],
            "tenant_id":tenant_id
        },
        {
            "$addToSet":{
                "role_ids":{"$each":role_ids}
            }
        }
    )

    return{
        "message":"roles assigned successfully",
        "user_role":user_id,
        "role_ids":[str(rid) for rid in role_ids]
    }

@app.get("/test-permission")
async def test_permission(
    current_user: dict =Depends(require_permission("project:create"))
):
    return {
        "message": "you have project create permission"
    }