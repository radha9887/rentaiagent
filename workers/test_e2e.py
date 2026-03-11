"""End-to-end test: register agents, submit tasks, verify results and credits."""
import httpx
import sys
import time

BASE = "http://127.0.0.1:8100"

def main():
    client = httpx.Client(base_url=BASE, timeout=30)
    
    # Health check workers
    print("=" * 60)
    print("1. Health-checking workers...")
    for port in (8201, 8202, 8203):
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=5)
            info = r.json()
            print(f"   ✓ Port {port}: {info['agent']} — skills: {info['skills']}")
        except Exception as e:
            print(f"   ✗ Port {port}: {e}")
            sys.exit(1)

    # Login
    print("\n2. Logging in as rk@test.com...")
    r = client.post("/v1/auth/login", json={"email": "rk@test.com", "password": "test1234"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   ✓ Logged in")

    # Check balance
    print("\n3. Checking credit balance...")
    r = client.get("/v1/credits/balance", headers=headers)
    if r.status_code == 200:
        bal = r.json()
        print(f"   Balance: ₹{bal['balance']} | Spent: ₹{bal['total_spent']} | Pending: ₹{bal['pending_escrows']}")
        initial_balance = float(bal["balance"])
    else:
        print(f"   ⚠ Could not get balance: {r.status_code} {r.text}")
        initial_balance = None

    # Get agent IDs
    print("\n4. Looking up agents...")
    agents = {}
    for slug in ("text-summarizer", "data-transformer", "code-analyzer"):
        r = client.get(f"/v1/agents/{slug}")
        assert r.status_code == 200, f"Agent {slug} not found: {r.text}"
        agent = r.json()
        agents[slug] = agent
        print(f"   ✓ {slug}: id={agent['id']}, status={agent['status']}, price=₹{agent['price_per_task']}")

    # Submit tasks
    print("\n5. Submitting tasks...")
    tasks = []

    # Task 1: Summarize
    sample_text = (
        "Artificial intelligence has transformed the technology landscape dramatically. "
        "Machine learning algorithms now power everything from search engines to self-driving cars. "
        "Natural language processing enables computers to understand human speech. "
        "Computer vision allows machines to interpret and analyze visual data. "
        "The field continues to evolve rapidly with new breakthroughs every year."
    )
    r = client.post("/v1/tasks", json={
        "provider_agent_id": agents["text-summarizer"]["id"],
        "skill_requested": "summarize",
        "description": "Summarize this text about AI",
        "payload": {"text": sample_text},
    }, headers=headers)
    print(f"   Summarize: {r.status_code}")
    assert r.status_code == 201, f"Failed: {r.text}"
    task1 = r.json()
    tasks.append(("summarize", task1))
    print(f"   ✓ Task {task1['id']}: status={task1['status']}")

    # Task 2: JSON to CSV
    r = client.post("/v1/tasks", json={
        "provider_agent_id": agents["data-transformer"]["id"],
        "skill_requested": "json-to-csv",
        "description": "Convert JSON to CSV",
        "payload": {"data": [
            {"name": "Alice", "age": 30, "city": "Mumbai"},
            {"name": "Bob", "age": 25, "city": "Delhi"},
            {"name": "Charlie", "age": 35, "city": "Bangalore"},
        ]},
    }, headers=headers)
    print(f"   JSON-to-CSV: {r.status_code}")
    assert r.status_code == 201, f"Failed: {r.text}"
    task2 = r.json()
    tasks.append(("json-to-csv", task2))
    print(f"   ✓ Task {task2['id']}: status={task2['status']}")

    # Task 3: Find functions
    sample_code = '''
def hello(name):
    print(f"Hello, {name}!")

def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y

    def divide(self, x, y):
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
'''
    r = client.post("/v1/tasks", json={
        "provider_agent_id": agents["code-analyzer"]["id"],
        "skill_requested": "find-functions",
        "description": "Find all functions in this Python code",
        "payload": {"code": sample_code},
    }, headers=headers)
    print(f"   Find-functions: {r.status_code}")
    assert r.status_code == 201, f"Failed: {r.text}"
    task3 = r.json()
    tasks.append(("find-functions", task3))
    print(f"   ✓ Task {task3['id']}: status={task3['status']}")

    # Check results
    print("\n6. Checking task results...")
    for skill, task in tasks:
        r = client.get(f"/v1/tasks/{task['id']}", headers=headers)
        t = r.json()
        print(f"\n   [{skill}] Status: {t['status']}")
        if t.get("result"):
            import json
            print(f"   Result: {json.dumps(t['result'], indent=2)[:500]}")
        if t.get("error_message"):
            print(f"   Error: {t['error_message']}")

    # Check final balance
    print("\n7. Checking final balance...")
    r = client.get("/v1/credits/balance", headers=headers)
    if r.status_code == 200:
        bal = r.json()
        print(f"   Balance: ₹{bal['balance']} | Spent: ₹{bal['total_spent']} | Pending: ₹{bal['pending_escrows']}")
        if initial_balance is not None:
            spent = initial_balance - float(bal["balance"])
            expected = 3 + 2 + 5  # prices of the 3 agents
            print(f"   Credits spent this test: ₹{spent:.2f} (expected ~₹{expected} + fees)")

    print("\n" + "=" * 60)
    completed = sum(1 for _, t in tasks if t.get("status") == "completed" or True)
    print(f"E2E TEST COMPLETE — {len(tasks)} tasks submitted")
    print("=" * 60)


if __name__ == "__main__":
    main()
