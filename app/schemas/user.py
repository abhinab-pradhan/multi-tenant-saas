from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password:str
    tenant_id:str

class UserLogin(BaseModel):
    email:str
    password:str
    tenant_id:str

class UserRoleAssign(BaseModel):
    role_ids: list[str]= Field(min_length=1)