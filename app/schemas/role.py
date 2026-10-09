from pydantic import BaseModel, Field

class RoleCreate(BaseModel):
    name: str=Field(min_length=2, max_length=50)
    description: str=Field(default="", max_length=300)