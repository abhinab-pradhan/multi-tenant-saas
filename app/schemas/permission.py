from pydantic import BaseModel, Field

class PermissionCreate(BaseModel):
    name: str=Field(min_length=3, max_length=100)
    description: str= Field(default="", max_length=300)

    