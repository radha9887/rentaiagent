"""API Tester Agent - Port 8211"""
import time
from base_worker import create_worker_app
import httpx


def http_request(payload: dict) -> dict:
    url = payload.get("url", "")
    method = payload.get("method", "GET").upper()
    headers = payload.get("headers", {})
    body = payload.get("body")
    if not url:
        raise ValueError("No URL provided")
    start = time.time()
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.request(method, url, headers=headers, json=body if body else None)
    elapsed = round((time.time() - start) * 1000, 2)
    try:
        resp_body = r.json()
    except Exception:
        resp_body = r.text[:2000]
    return {"status": r.status_code, "headers": dict(r.headers), "body": resp_body, "time_ms": elapsed}


def check_endpoint(payload: dict) -> dict:
    url = payload.get("url", "")
    if not url:
        raise ValueError("No URL provided")
    start = time.time()
    redirect_chain = []
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            r = client.get(url)
            for resp in r.history:
                redirect_chain.append({"url": str(resp.url), "status": resp.status_code})
        elapsed = round((time.time() - start) * 1000, 2)
        ssl_valid = url.startswith("https://")
        return {"reachable": True, "status": r.status_code, "response_time_ms": elapsed, "ssl_valid": ssl_valid, "redirect_chain": redirect_chain}
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 2)
        return {"reachable": False, "status": None, "response_time_ms": elapsed, "ssl_valid": False, "redirect_chain": [], "error": str(e)}


app = create_worker_app("api-tester", {
    "http-request": http_request,
    "check-endpoint": check_endpoint,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8211)
