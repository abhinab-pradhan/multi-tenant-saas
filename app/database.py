from pymongo import AsyncMongoClient
import os
from dotenv import load_dotenv
from app.core.config import settings

load_dotenv()

MONGODB_URL=os.getenv("MONGODB_URL")
DATABASE_NAME=os.getenv("DATABASE_NAME")

if not settings.MONGODB_URL:
    raise ValueError("MONGODB_URL is not configured")

if not settings.DATABASE_NAME:
    raise ValueError("DATABASE_NAME is not configured")

client= AsyncMongoClient(settings.MONGODB_URL)
db=client[settings.DATABASE_NAME]

async def create_indexes():
    await db.roles.create_index(
        [("tenant_id",1), ("name",1)],
        unique=True,
        name="unique_role_per_tenant"
    )

    await db.permissions.create_index(
        [("tenant_id",1), ("name",1)],
        unique=True,
        name="unique_permission_per_tenant"
    )

    await db.projects.create_index(
        [("tenant_id",1)],
        name="projects_by_tenant"
    )

    await db.users.create_index(
        [("tenant_id",1), ("email",1)],
        unique=True,
        name="unique_email_per_tenant"
    )

    await db.users.create_index(
        [
            ("tenant_id", 1),
            ("email", 1)
        ],
        unique=True,
        name="unique_email_per_tenant"
    )