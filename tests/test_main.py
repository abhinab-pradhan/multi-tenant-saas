from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user


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