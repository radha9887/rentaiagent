"""Base agent worker framework for RentAiAgent."""
import hashlib
import hmac
import json
import logging
from fastapi import FastAPI, Request, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

HMAC_SECRET = "raa-hmac-secret-change-in-prod-2026"


def create_worker_app(name: str, skill_handlers: dict) -> FastAPI:
    app = FastAPI(title=name)
    logger = logging.getLogger(name)

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": name, "skills": list(skill_handlers.keys())}

    @app.post("/handle")
    async def handle(request: Request):
        body = await request.body()
        
        # Verify HMAC
        sig = request.headers.get("X-RentAiAgent-Signature", "")
        expected = hmac.new(HMAC_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=401, detail="Invalid signature")

        data = json.loads(body)
        task_id = data.get("task_id", "unknown")
        skill = data.get("skill", "")
        payload = data.get("payload", {})
        
        logger.info(f"Task {task_id}: skill={skill}, payload_keys={list(payload.keys()) if payload else []}")

        handler = skill_handlers.get(skill)
        if not handler:
            return {"status": "failed", "error": f"Unknown skill: {skill}"}

        try:
            result = handler(payload)
            logger.info(f"Task {task_id}: completed")
            return {"status": "completed", "data": result}
        except Exception as e:
            logger.error(f"Task {task_id}: failed - {e}")
            return {"status": "failed", "error": str(e)}

    return app
