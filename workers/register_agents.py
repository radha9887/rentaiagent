"""Register the 3 worker agents via the RentAnAgent API."""
import httpx
import sys

BASE = "http://127.0.0.1:8100"

AGENTS = [
    {
        "name": "Text Summarizer",
        "slug": "text-summarizer",
        "description": "Summarizes text and extracts keywords using NLP techniques.",
        "endpoint_url": "http://127.0.0.1:8201/handle",
        "endpoint_type": "rest",
        "price_per_task": "3.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8201/health",
        "version": "1.0.0",
        "framework": "fastapi",
        "skills": [
            {"skill_tag": "summarize", "category": "nlp", "proficiency": 0.8},
            {"skill_tag": "extract-keywords", "category": "nlp", "proficiency": 0.8},
        ],
    },
    {
        "name": "Data Transformer",
        "slug": "data-transformer",
        "description": "Transforms data between JSON, CSV, and other formats.",
        "endpoint_url": "http://127.0.0.1:8202/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8202/health",
        "version": "1.0.0",
        "framework": "fastapi",
        "skills": [
            {"skill_tag": "json-to-csv", "category": "data", "proficiency": 0.9},
            {"skill_tag": "csv-to-json", "category": "data", "proficiency": 0.9},
            {"skill_tag": "format-json", "category": "data", "proficiency": 0.9},
        ],
    },
    {
        "name": "Code Analyzer",
        "slug": "code-analyzer",
        "description": "Analyzes source code: line counts, language detection, function extraction.",
        "endpoint_url": "http://127.0.0.1:8203/handle",
        "endpoint_type": "rest",
        "price_per_task": "5.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8203/health",
        "version": "1.0.0",
        "framework": "fastapi",
        "skills": [
            {"skill_tag": "count-lines", "category": "code", "proficiency": 0.9},
            {"skill_tag": "detect-language", "category": "code", "proficiency": 0.85},
            {"skill_tag": "find-functions", "category": "code", "proficiency": 0.85},
        ],
    },
]


def main():
    client = httpx.Client(base_url=BASE, timeout=30)
    
    # Login
    r = client.post("/v1/auth/login", json={"email": "rk@test.com", "password": "test1234"})
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Logged in as rk@test.com")

    agent_ids = []
    for agent_data in AGENTS:
        slug = agent_data["slug"]
        # Try to get existing
        r = client.get(f"/v1/agents/{slug}")
        if r.status_code == 200:
            # Update
            existing = r.json()
            agent_id = existing["id"]
            update = {k: v for k, v in agent_data.items() if k != "slug"}
            r = client.patch(f"/v1/agents/{slug}", json=update, headers=headers)
            if r.status_code == 200:
                print(f"✓ Updated {slug} ({agent_id})")
            else:
                print(f"✗ Update {slug} failed: {r.status_code} {r.text}")
        else:
            # Create
            r = client.post("/v1/agents", json=agent_data, headers=headers)
            if r.status_code == 201:
                agent_id = r.json()["id"]
                print(f"✓ Created {slug} ({agent_id})")
            else:
                print(f"✗ Create {slug} failed: {r.status_code} {r.text}")
                continue
        agent_ids.append(agent_id)

    # Approve all agents (admin endpoint)
    for aid in agent_ids:
        r = client.post(f"/v1/admin/agents/{aid}/approve", headers=headers)
        if r.status_code == 200:
            print(f"✓ Approved {aid}")
        else:
            print(f"  Approve {aid}: {r.status_code} {r.text}")

    print(f"\nAll {len(agent_ids)} agents registered and approved.")


if __name__ == "__main__":
    main()
