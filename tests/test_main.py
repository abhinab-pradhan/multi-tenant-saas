from fastapi.testclient import TestClient
from bson import ObjectId
from unittest.mock import AsyncMock
from types import SimpleNamespace
from fastapi import HTTPException

from app.main import app
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_project_read, require_permission, require_user_manage, require_project_update, require_project_delete
from app.dependencies.permissions import require_role_manage

import app.routers.projects as projects_module
import app.main as main_module


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

def test_employee_cannot_create_user():
    async def fake_permission_checker():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="permission required user:manage"
        )
    app.dependency_overrides[require_user_manage] = fake_permission_checker


    try:
        response= client.post(
            "/users",
            json={
                "email":"employee-test@example.com",
                "password":"strongPassword123",
                "tenant_id":str(ObjectId())
            }
        )
        assert response.status_code==403

    finally:
        app.dependency_overrides.clear()

def test_user_creation_uses_authenticated_tenant():
    tenant_a= ObjectId()
    tenant_b= ObjectId()

    fake_user={
        "_id": ObjectId(),
        "email": "admin@example.com",
        "tenant_id": tenant_a,
        "role_ids":[ObjectId()]
    }

    async def fake_current_user():
        return fake_user

    mock_tenant_find= AsyncMock(return_value= {"_id":tenant_a})
    mock_user_find= AsyncMock(return_value=None)
    mock_user_insert= AsyncMock(
        return_value=SimpleNamespace(inserted_id=ObjectId())
    )

    fake_db= SimpleNamespace(
        tenants=SimpleNamespace(find_one=mock_tenant_find),
        users=SimpleNamespace(
            find_one=mock_user_find,
            insert_one=mock_user_insert
        )
    )

    #override the exact dependency used by the route
    #user_manage_depedency= main_module.require_permission("user:manage")
    app.dependency_overrides[require_user_manage]= fake_current_user

    original_db= main_module.db
    main_module.db = fake_db

    try:
        response= client.post(
            "/users",
            json={
                "email":"newuser@example.com",
                "password":"strongPassword123",
                "tenant_id":str(tenant_b)
            }
        )

        assert response.status_code in (200,201), response.text

        mock_tenant_find.assert_awaited_once()
        mock_user_find.assert_awaited_once()
        mock_user_insert.assert_awaited_once()

        #check the actual inserted document
        inserted_user= mock_user_insert.call_args.args[0]
        assert inserted_user["tenant_id"] == tenant_a

    finally:
        main_module.db= original_db
        app.dependency_overrides.clear()

def test_user_cannot_access_another_tenants_projects():
    tenant_a= ObjectId()
    tenant_b= ObjectId()
    project_id= ObjectId()

    fake_user={
        "_id":ObjectId(),
        "tenant_id":tenant_a,
        "role_ids":[ObjectId()]
    }

    async def fake_current_user():
        return fake_user

    mock_project_find= AsyncMock(return_value=None)

    fake_db= SimpleNamespace(

        projects=SimpleNamespace(
            find_one=mock_project_find
        )
    )

    app.dependency_overrides[require_project_read]= fake_current_user

    original_db= projects_module.db
    projects_module.db= fake_db

    try:
        response= client.get(f"/projects/{project_id}")

        assert response.status_code==404, response.text

        #the lookup must be scoped to the authenticated tenant
        query= mock_project_find.call_args.args[0]
        assert query["_id"] == project_id
        assert query["tenant_id"] == tenant_a

    finally:
        projects_module.db=original_db
        app.dependency_overrides.clear()

#Test cross-tenant project updates
def test_user_cannot_update_another_tenants_project():
    tenant_a= ObjectId()
    tenant_b=ObjectId()
    project_id= ObjectId()

    tenant_b_project={
        "_id":project_id,
        "tenant_id":ObjectId(),
        "name":"tenant b private project"
    }

    async def fake_current_user():
        return{
            "_id":ObjectId(),
            "tenant_id":tenant_a,
            "role_ids": [ObjectId()]
        }

    async def fake_update_one(query, update):
        #the update query must be scoped to tenant A
        assert query["tenant_id"] == tenant_a

        #tenant B's project cannot match tenant A's query
        assert not(
            query["_id"] == tenant_b_project["_id"]
            and query["tenant_id"] == tenant_b_project["tenant_id"]
        )

        return SimpleNamespace(matched_count=0)

    mock_update= AsyncMock(side_effect= fake_update_one)

    fake_db=SimpleNamespace(
        projects=SimpleNamespace(update_one=mock_update)
    )

    app.dependency_overrides[require_project_update]= fake_current_user

    original_db= projects_module.db
    projects_module.db=fake_db

    try:
        response= client.put(
            f"/projects/{project_id}",
            json={"name":"unauthorized change"}
        )

        assert response.status_code==404, response.text
        mock_update.assert_awaited_once()

        query=mock_update.call_args.args[0]
        assert query["_id"]==project_id
        assert query["tenant_id"] == tenant_a

    finally:
        projects_module.db=original_db
        app.dependency_overrides.clear()

def test_user_cannot_delete_another_tenants_project():
    tenant_a= ObjectId()
    tenant_b=ObjectId()
    project_id= ObjectId()

    tenant_b_project={
        "_id":project_id,
        "tenant_id":tenant_b,
        "name":"tenant b private project"
    }

    async def fake_current_user():
        return{
            "_id":ObjectId(),
            "tenant_id":tenant_a,
            "role_ids":[ObjectId()]
        }

    async def fake_delete_one(query):
        #the  delete query must be scoped to tenant A
        assert query["tenant_id"] == tenant_a

        assert not(
            query["_id"] == tenant_b_project["_id"]
            and query["tenant_id"] == tenant_b_project["tenant_id"]
        )

        return SimpleNamespace(deleted_count=0)

    mock_delete=AsyncMock(side_effect=fake_delete_one)

    fake_db= SimpleNamespace(
        projects=SimpleNamespace(delete_one=mock_delete)
    )

    app.dependency_overrides[require_project_delete]= fake_current_user

    original_db= projects_module.db
    projects_module.db= fake_db

    try:
        response=client.delete(f"/projects/{project_id}")
        assert response.status_code== 404, response.text
        mock_delete.assert_awaited_once()

        query= mock_delete.call_args.args[0]
        assert query["_id"] == project_id
        assert query["tenant_id"] == tenant_a

    finally:
        projects_module.db= original_db
        app.dependency_overrides.clear()

#test for unauthorized role management
def test_employee_cannot_manage_roles():
    async def fake_permission_denied():
        raise HTTPException(
            status_code=403,
            detail="permission required role:manage"
        )

    app.dependency_overrides[require_role_manage]=(
        fake_permission_denied
    )

    try:
        response= client.post(
            "/roles/",
            json={
                "name":"employee-test",
                "description":"test role"
            }
        )

        assert response.status_code== 403, response.text

    finally:
        app.dependency_overrides.clear()