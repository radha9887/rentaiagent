#!/usr/bin/env python3
"""Standalone test script for the MCP SSE server."""

import json
import sys
import threading
import time

import httpx

BASE_URL = "http://localhost:8000"
API_KEY = sys.argv[1] if len(sys.argv) > 1 else "raa_live_test_key"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def main():
    session_id = None
    responses: list[dict] = []

    # Connect to SSE in a background thread
    def sse_listener():
        nonlocal session_id
        with httpx.stream("GET", f"{BASE_URL}/mcp/sse", headers=HEADERS, timeout=60) as r:
            for line in r.iter_lines():
                if line.startswith("event: endpoint"):
                    continue
                if line.startswith("data: ") and session_id is None:
                    # First data line is the endpoint
                    endpoint = line[6:]
                    if "session_id=" in endpoint:
                        session_id = endpoint.split("session_id=")[1]
                        print(f"✅ Connected! Session: {session_id}")
                        continue
                if line.startswith("data: "):
                    try:
                        msg = json.loads(line[6:])
                        responses.append(msg)
                        print(f"📩 Response: {json.dumps(msg, indent=2)}")
                    except json.JSONDecodeError:
                        pass

    t = threading.Thread(target=sse_listener, daemon=True)
    t.start()

    # Wait for SSE connection
    for _ in range(50):
        if session_id:
            break
        time.sleep(0.1)
    else:
        print("❌ Failed to connect to SSE endpoint")
        sys.exit(1)

    def send(method: str, params: dict | None = None, req_id: int = 1):
        msg = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params:
            msg["params"] = params
        r = httpx.post(f"{BASE_URL}/mcp/messages?session_id={session_id}", json=msg, timeout=30)
        print(f"📤 Sent {method} → HTTP {r.status_code}")
        time.sleep(1)  # wait for SSE response

    # 1. Initialize
    send("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "0.1"}}, req_id=1)

    # 2. Initialized notification
    msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    httpx.post(f"{BASE_URL}/mcp/messages?session_id={session_id}", json=msg, timeout=10)
    print("📤 Sent notifications/initialized")

    # 3. Tools list
    send("tools/list", req_id=2)

    # 4. Search agents
    send("tools/call", {"name": "search_agents", "arguments": {"skill": "summarization"}}, req_id=3)

    print(f"\n🏁 Done. Received {len(responses)} responses.")


if __name__ == "__main__":
    main()
