import os
os.chdir("/home/openclaw/workspace/rentanagent")

import pytest
import uuid
import sys
sys.path.insert(0, "/home/openclaw/workspace/rentanagent")

from fastapi.testclient import TestClient
from main import app

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient — runs app in-process for coverage."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session")
def unique_suffix():
    return uuid.uuid4().hex[:8]

@pytest.fixture(scope="session")
def unique_email(unique_suffix):
    return f"pytest-{unique_suffix}@example.com"

@pytest.fixture(scope="session")
def registered_user(client, unique_email):
    resp = client.post("/v1/auth/register", json={
        "email": unique_email,
        "password": "TestPass123!",
        "display_name": "Pytest User"
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    login = client.post("/v1/auth/login", json={
        "email": unique_email,
        "password": "TestPass123!"
    })
    assert login.status_code == 200
    login_data = login.json()
    return {
        "email": unique_email,
        "raw_key": data.get("raw_key"),
        "jwt": login_data["token"],
        "user": login_data["user"],
    }

@pytest.fixture(scope="session")
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['jwt']}"}

@pytest.fixture(scope="session")
def second_user(client):
    email = f"test2-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/v1/auth/register", json={
        "email": email, "password": "TestPass123!", "display_name": "Test User 2"
    })
    assert resp.status_code == 201
    login = client.post("/v1/auth/login", json={
        "email": email, "password": "TestPass123!"
    })
    assert login.status_code == 200
    login_data = login.json()
    return {
        "email": email,
        "jwt": login_data.get("token"),
        "headers": {"Authorization": f"Bearer {login_data.get('token')}"},
    }

@pytest.fixture(scope="session")
def agent_slug(unique_suffix):
    return f"pytest-agent-{unique_suffix}"

@pytest.fixture(scope="session")
def created_agent(client, auth_headers, agent_slug):
    resp = client.post("/v1/agents", headers=auth_headers, json={
        "name": "Pytest Agent",
        "slug": agent_slug,
        "description": "Agent for pytest",
        "endpoint_url": "https://example.com/agent",
        "health_check_url": "https://httpbin.org/status/200",
        "skills": [{"skill_tag": "general"}],
    })
    assert resp.status_code == 201, f"Agent creation failed: {resp.text}"
    return resp.json()

@pytest.fixture(scope="session")
def created_task(client, auth_headers, created_agent):
    resp = client.post("/v1/tasks", headers=auth_headers, json={
        "provider_agent_id": created_agent["id"],
        "skill_requested": "general",
        "description": "Pytest test task",
    })
    assert resp.status_code == 201, f"Task creation failed: {resp.text}"
    return resp.json()
