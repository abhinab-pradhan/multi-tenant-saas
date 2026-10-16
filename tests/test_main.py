from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app
from app.dependencies.auth import get_current_user
from app.database import db
from app.dependencies.permissions import require_permission
from app.dependencies.permissions import require_project_read
from app.database import db


client=TestClient(app)

def test_root_endpoint():
    response=client.get("/")
    assert response.status_code==200

def test_me_without_token():
    response=client.get("/me")
    assert response.status_code==401

def test_me_with_invalid_token():
    response=client.get(
        "/me",
        headers={
            "authorization":"bearer invalid_token"
        }
    )
    assert response.status_code==401

def test_project_create_denied_without_permission():
    async def fake_user():
        return{
            "_id":"test-user",
            "tenant_id":"test-tenant",
            "role_ids":[]
        }

    app.dependency_overrides[get_current_user]= fake_user

    try:
        response=client.post(
            "/projects/",
            json={
                "name":"test project",
                "description":"RBAC test"
            }
        )
        assert response.status_code==403

    finally:
        app.dependency_overrides.clear()

def test_cannot_access_another_tenants_project():
    tenant_a = ObjectId()
    tenant_b = ObjectId()
    project_id = ObjectId()  # Fixed: define project_id

    async def fake_project_reader():
        return {
            "_id": ObjectId(),
            "tenant_id": tenant_a,
            "role_ids": []
        }

    app.dependency_overrides[require_project_read] = fake_project_reader

    async def fake_find_one(query):
        # The project belongs to Tenant B, not Tenant A.
        assert query["_id"] == project_id
        assert query["tenant_id"] == tenant_a
        return None

    original_find_one = db.projects.find_one
    db.projects.find_one = fake_find_one

    try:
        response = client.get(f"/projects/{project_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "project not found"

    finally:
        db.projects.find_one = original_find_one
        app.dependency_overrides.clear()