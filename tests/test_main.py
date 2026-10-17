from fastapi.testclient import TestClient
from bson import ObjectId
from unittest.mock import AsyncMock
from types import SimpleNamespace

from app.main import app
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_project_read
import app.routers.projects as projects_module


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200


def test_me_without_token():
    response = client.get("/me")
    assert response.status_code == 401


def test_me_with_invalid_token():
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_project_create_denied_without_permission():
    async def fake_user():
        return {
            "_id": "test-user",
            "tenant_id": "test-tenant",
            "role_ids": []
        }

    app.dependency_overrides[get_current_user] = fake_user

    try:
        response = client.post(
            "/projects/",
            json={
                "name": "test project",
                "description": "RBAC test"
            }
        )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()



def test_cannot_access_another_tenants_project():
    tenant_a = ObjectId()
    tenant_b = ObjectId()
    project_id = ObjectId()

    tenant_b_project = {
        "_id": project_id,
        "tenant_id": tenant_b,
        "name": "Tenant B Project",
        "description": "private project",
        "created_by": ObjectId()
    }

    async def fake_project_reader():
        return {
            "_id": ObjectId(),
            "tenant_id": tenant_a,
            "role_ids": []
        }

    async def fake_find_one(query):
        # The endpoint must include tenant_id in its query.
        if (
            query.get("_id") == project_id
            and query.get("tenant_id") == tenant_a
        ):
            return None

        # Simulate a project belonging to another tenant
        # if the query incorrectly omits tenant isolation.
        if (
            query.get("_id") == project_id
            and "tenant_id" not in query
        ):
            return tenant_b_project

        return None

    mock_find_one = AsyncMock(side_effect=fake_find_one)

    fake_db = SimpleNamespace(
        projects=SimpleNamespace(find_one=mock_find_one)
    )

    app.dependency_overrides[require_project_read] = fake_project_reader
    original_db = projects_module.db
    projects_module.db = fake_db

    try:
        response = client.get(f"/projects/{project_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "project not found"

        mock_find_one.assert_awaited_once()

        query = mock_find_one.call_args.args[0]
        assert query["_id"] == project_id
        assert query["tenant_id"] == tenant_a

    finally:
        projects_module.db = original_db
        app.dependency_overrides.clear()


def test_user_can_access_project_in_own_tenant():
    tenant_a = ObjectId()
    project_id = ObjectId()

    test_project = {
        "_id": project_id,
        "tenant_id": tenant_a,
        "name": "tenant A project",
        "description": "private project",
        "created_by": ObjectId()
    }

    async def fake_project_reader():
        return {
            "_id": ObjectId(),
            "tenant_id": tenant_a,
            "role_ids": []
        }

    mock_find_one = AsyncMock(return_value=test_project)

    fake_db = SimpleNamespace(
        projects=SimpleNamespace(find_one=mock_find_one)
    )

    app.dependency_overrides[require_project_read] = fake_project_reader
    original_db = projects_module.db
    projects_module.db = fake_db

    try:
        response = client.get(f"/projects/{project_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "tenant A project"
        assert response.json()["tenant_id"] == str(tenant_a)

        mock_find_one.assert_awaited_once()

        query = mock_find_one.call_args.args[0]
        assert query["_id"] == project_id
        assert query["tenant_id"] == tenant_a

    finally:
        projects_module.db = original_db
        app.dependency_overrides.clear()