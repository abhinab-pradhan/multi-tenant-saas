from pymongo import AsyncMongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL=os.getenv("MONGODB_URL")
DATABASE_NAME=os.getenv("DATABASE_NAME")

client=AsyncMongoClient(MONGODB_URL)

db=client[DATABASE_NAME]

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