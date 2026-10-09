from fastapi import FastAPI, HTTPException, Depends
from bson import ObjectId

from app.database import client,db
from app.schemas.tenant import TenantCreate
from app.schemas.user import UserCreate, UserLogin
from app.core.security import hash_password, verify_password, create_access_token
from app.dependencies.auth import get_current_user
from app.routers.projects import router as projects_router


app=FastAPI(
    title="Multi-Tenant SaaS API",
    version="1.0"
)

app.include_router(projects_router)

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
        "tenant_id":ObjectId(user.tenant_id)
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