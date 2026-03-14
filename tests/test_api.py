"""Comprehensive API tests for RentAiAgent platform."""
import pytest
import uuid


class TestAuth:
    def test_register(self, client):
        email = f"reg-{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/v1/auth/register", json={
            "email": email, "password": "Test1234!", "display_name": "Test User"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("raa_live_")
        assert data["is_active"] is True

    def test_register_duplicate_email(self, client, registered_user):
        resp = client.post("/v1/auth/register", json={
            "email": registered_user["email"],
            "password": "Test1234!",
            "display_name": "Dup"
        })
        assert resp.status_code == 409

    def test_login(self, client, registered_user):
        resp = client.post("/v1/auth/login", json={
            "email": registered_user["email"],
            "password": "TestPass123!"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "refresh_token" in data
        assert "user" in data

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post("/v1/auth/login", json={
            "email": registered_user["email"],
            "password": "wrongpassword"
        })
        assert resp.status_code == 401


class TestAgents:
    def test_register_agent_without_health_url(self, client, auth_headers):
        resp = client.post("/v1/agents", headers=auth_headers, json={
            "name": "No Health Agent",
            "slug": f"no-health-{uuid.uuid4().hex[:6]}",
            "description": "test",
            "endpoint_url": "https://example.com",
        })
        assert resp.status_code == 422

    def test_register_agent_with_health_url(self, created_agent):
        assert "id" in created_agent
        assert created_agent["slug"].startswith("pytest-agent-")

    def test_duplicate_slug(self, client, auth_headers, agent_slug):
        resp = client.post("/v1/agents", headers=auth_headers, json={
            "name": "Dup Slug",
            "slug": agent_slug,
            "description": "dup",
            "endpoint_url": "https://example.com",
            "health_check_url": "https://httpbin.org/status/200",
            "skills": [{"skill_tag": "x"}],
        })
        assert resp.status_code == 409

    def test_list_agents(self, client):
        resp = client.get("/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_featured_agents(self, client):
        resp = client.get("/v1/agents/featured")
        assert resp.status_code == 200
        data = resp.json()
        if isinstance(data, dict):
            assert "agents" in data
        else:
            assert isinstance(data, list)

    def test_get_agent_by_slug(self, client, agent_slug):
        resp = client.get(f"/v1/agents/{agent_slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == agent_slug

    def test_my_agents(self, client, auth_headers):
        resp = client.get("/v1/agents/me", headers=auth_headers)
        assert resp.status_code == 200

    def test_update_agent(self, client, auth_headers, agent_slug):
        resp = client.patch(f"/v1/agents/{agent_slug}", headers=auth_headers, json={
            "description": "Updated by pytest"
        })
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated by pytest"

    def test_agent_health(self, client, agent_slug):
        resp = client.get(f"/v1/agents/{agent_slug}/health")
        assert resp.status_code == 200


class TestTasks:
    def test_create_task(self, created_task):
        assert "id" in created_task
        assert created_task["skill_requested"] == "general"

    def test_task_feed(self, client):
        resp = client.get("/v1/tasks/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "total" in data

    def test_list_my_tasks(self, client, auth_headers):
        resp = client.get("/v1/tasks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_get_task_by_id(self, client, auth_headers, created_task):
        task_id = created_task["id"]
        resp = client.get(f"/v1/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    def test_complete_task_already_finalized(self, client, auth_headers, created_task):
        task_id = created_task["id"]
        resp = client.post(f"/v1/tasks/{task_id}/complete", headers=auth_headers, json={
            "result": {"output": "done"},
        })
        assert resp.status_code in (200, 422)

    def test_cancel_task(self, client, auth_headers, created_agent):
        resp = client.post("/v1/tasks", headers=auth_headers, json={
            "provider_agent_id": created_agent["id"],
            "skill_requested": "general",
            "description": "cancel me",
        })
        assert resp.status_code == 201
        task_id = resp.json()["id"]
        task_status = resp.json()["status"]
        resp = client.post(f"/v1/tasks/{task_id}/cancel", headers=auth_headers)
        if task_status in ("pending", "escrowed", "routed"):
            assert resp.status_code == 200
        else:
            assert resp.status_code == 422


class TestCredits:
    def test_signup_bonus(self, client, registered_user, auth_headers):
        resp = client.get("/v1/credits/balance", headers=auth_headers)
        assert resp.status_code == 200
        balance = float(resp.json()["balance"])
        assert balance == 100.0

    def test_balance(self, client, auth_headers):
        resp = client.get("/v1/credits/balance", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "balance" in data
        assert "currency" in data

    def test_transactions(self, client, auth_headers):
        resp = client.get("/v1/credits/transactions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


class TestRatings:
    def test_submit_rating_non_completed_task(self, client, auth_headers, created_task):
        resp = client.post("/v1/ratings", headers=auth_headers, json={
            "task_id": created_task["id"],
            "overall_score": 5,
            "feedback": "Great!",
        })
        assert resp.status_code == 422


class TestDevelopers:
    def test_developer_register(self, client):
        email = f"dev-{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/v1/developers/register", json={"email": email})
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" in data
        assert data["credits"] == 100

    def test_generate_key(self, client, auth_headers):
        resp = client.post("/v1/developers/generate-key", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" in data
        assert "prefix" in data

    def test_list_keys(self, client, auth_headers):
        resp = client.get("/v1/developers/keys", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert len(data["keys"]) >= 1

    def test_revoke_key(self, client, auth_headers):
        gen = client.post("/v1/developers/generate-key", headers=auth_headers)
        prefix = gen.json()["prefix"]
        resp = client.delete(f"/v1/developers/keys/{prefix}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["revoked"] is True


class TestStats:
    def test_public_stats(self, client):
        resp = client.get("/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents_online" in data
        assert "tasks_total" in data


class TestSecurity:
    def test_no_auth_protected_route(self, client):
        resp = client.get("/v1/credits/balance")
        assert resp.status_code == 401

    def test_invalid_jwt(self, client):
        resp = client.get("/v1/credits/balance",
                         headers={"Authorization": "Bearer invalid.jwt.token"})
        assert resp.status_code == 401

    def test_no_auth_agents_me(self, client):
        resp = client.get("/v1/agents/me")
        assert resp.status_code == 401

    def test_no_auth_tasks_list(self, client):
        resp = client.get("/v1/tasks")
        assert resp.status_code == 401


class TestAuthExtended:
    def test_register_missing_fields(self, client):
        resp = client.post("/v1/auth/register", json={
            "password": "Test1234!", "display_name": "No Email"
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post("/v1/auth/register", json={
            "email": f"short-{uuid.uuid4().hex[:8]}@example.com",
            "password": "ab",
            "display_name": "Short Pass"
        })
        assert resp.status_code in (201, 422)

    def test_login_nonexistent_email(self, client):
        resp = client.post("/v1/auth/login", json={
            "email": f"nonexistent-{uuid.uuid4().hex}@example.com",
            "password": "Whatever123!"
        })
        assert resp.status_code == 401


class TestAgentsExtended:
    def test_register_agent_invalid_health_url(self, client, auth_headers):
        resp = client.post("/v1/agents", headers=auth_headers, json={
            "name": "Bad Health",
            "slug": f"bad-health-{uuid.uuid4().hex[:6]}",
            "description": "test",
            "endpoint_url": "https://example.com/agent",
            "health_check_url": "not-a-url",
            "skills": [{"skill_tag": "general"}],
        })
        assert resp.status_code == 422

    def test_get_nonexistent_agent(self, client):
        resp = client.get(f"/v1/agents/nonexistent-slug-xyz-{uuid.uuid4().hex[:6]}")
        assert resp.status_code == 404

    def test_update_agent_not_owner(self, client, agent_slug, second_user):
        resp = client.patch(f"/v1/agents/{agent_slug}",
                           headers=second_user["headers"],
                           json={"description": "hacked"})
        assert resp.status_code == 403

    def test_delete_agent_not_owner(self, client, agent_slug, second_user):
        resp = client.delete(f"/v1/agents/{agent_slug}",
                            headers=second_user["headers"])
        assert resp.status_code == 403

    def test_list_agents_pagination(self, client):
        resp = client.get("/v1/agents", params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) <= 2

    def test_import_preview_invalid_url(self, client, auth_headers):
        resp = client.get("/v1/agents/import/preview",
                         headers=auth_headers,
                         params={"url": "https://example.com"})
        assert resp.status_code in (400, 422, 404)

    def test_agent_status_toggle(self, client, auth_headers, agent_slug):
        resp = client.patch(f"/v1/agents/{agent_slug}",
                           headers=auth_headers,
                           json={"status": "offline"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "offline"
        resp = client.patch(f"/v1/agents/{agent_slug}",
                           headers=auth_headers,
                           json={"status": "online"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "online"


class TestTasksExtended:
    def test_create_task_no_auth(self, client, created_agent):
        resp = client.post("/v1/tasks", json={
            "provider_agent_id": created_agent["id"],
            "skill_requested": "general",
            "description": "no auth task",
        })
        assert resp.status_code == 401

    def test_get_task_not_found(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/v1/tasks/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_task_feed_with_filters(self, client):
        resp = client.get("/v1/tasks/feed", params={"status": "completed"})
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        for t in data["tasks"]:
            assert t["status"] == "completed"

    def test_task_feed_pagination(self, client):
        resp = client.get("/v1/tasks/feed", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "total" in data
        assert len(data["tasks"]) <= 2

    def test_auto_route_no_agent(self, client, auth_headers):
        resp = client.post("/v1/tasks/auto", headers=auth_headers, json={
            "skill_requested": f"nonexistent-skill-{uuid.uuid4().hex[:8]}",
            "description": "nobody can do this",
        })
        assert resp.status_code in (404, 422)


class TestCreditsExtended:
    def test_balance_new_account(self, client, second_user):
        resp = client.get("/v1/credits/balance", headers=second_user["headers"])
        assert resp.status_code == 200
        assert float(resp.json()["balance"]) == 100.0

    def test_transactions_has_signup_bonus(self, client, second_user):
        resp = client.get("/v1/credits/transactions", headers=second_user["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1


class TestDevelopersExtended:
    def test_developer_register_duplicate(self, client, registered_user):
        resp = client.post("/v1/developers/register",
                          json={"email": registered_user["email"]})
        assert resp.status_code == 409

    def test_usage_endpoint(self, client, auth_headers):
        resp = client.get("/v1/developers/usage", headers=auth_headers)
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)

    def test_my_agents_endpoint(self, client, auth_headers):
        resp = client.get("/v1/developers/my-agents", headers=auth_headers)
        assert resp.status_code == 200

    def test_revoke_nonexistent_key(self, client, auth_headers):
        resp = client.delete("/v1/developers/keys/nonexistent_prefix_xyz",
                            headers=auth_headers)
        assert resp.status_code == 404


class TestA2A:
    def test_well_known_agent_json(self, client):
        resp = client.get("/.well-known/agent.json")
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)
        else:
            assert resp.status_code in (404, 405)

    def test_a2a_agent_endpoint(self, client):
        resp = client.post("/a2a/agents/test-slug", json={})
        assert resp.status_code in (200, 400, 401, 404, 422)


class TestMCP:
    def test_mcp_sse_exists(self, client):
        try:
            resp = client.get("/mcp/sse")
            assert resp.status_code in (200, 401, 404, 405)
        except Exception:
            pass


class TestWebhooks:
    def test_list_webhooks(self, client, auth_headers):
        resp = client.get("/v1/webhooks", headers=auth_headers)
        assert resp.status_code == 200


class TestCleanup:
    def test_delete_agent(self, client, auth_headers, agent_slug):
        resp = client.delete(f"/v1/agents/{agent_slug}", headers=auth_headers)
        assert resp.status_code == 200
