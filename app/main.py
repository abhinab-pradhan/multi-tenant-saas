from fastapi import FastAPI
from app.database import client,db
from app.schemas.tenant import TenantCreate
from bson import ObjectId
from app.schemas.user import UserCreate
from app.core.security import hash_password

app=FastAPI(
    title="Multi-Tenant SaaS API",
    version="1.0"
)

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