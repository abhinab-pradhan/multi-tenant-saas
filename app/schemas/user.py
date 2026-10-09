from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password:str
    tenant_id:str

class UserLogin(BaseModel):
    email:str
    password:str