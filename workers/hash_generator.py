"""Hash Generator Agent - Port 8207"""
import hashlib
import uuid
import base64
from base_worker import create_worker_app


def hash_text(payload: dict) -> dict:
    text = payload.get("text", "")
    algorithm = payload.get("algorithm", "sha256")
    if not text:
        raise ValueError("No text provided")
    if algorithm not in ("md5", "sha256", "sha512"):
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    h = hashlib.new(algorithm, text.encode()).hexdigest()
    return {"hash": h, "algorithm": algorithm}


def generate_uuid(payload: dict) -> dict:
    version = payload.get("version", 4)
    if version == 1:
        result = str(uuid.uuid1())
    else:
        result = str(uuid.uuid4())
        version = 4
    return {"uuid": result, "version": version}


def encode_base64(payload: dict) -> dict:
    text = payload.get("text", "")
    action = payload.get("action", "encode")
    if not text:
        raise ValueError("No text provided")
    if action == "decode":
        result = base64.b64decode(text).decode("utf-8", errors="replace")
    else:
        result = base64.b64encode(text.encode()).decode()
    return {"result": result, "action": action}


app = create_worker_app("hash-generator", {
    "hash-text": hash_text,
    "generate-uuid": generate_uuid,
    "encode-base64": encode_base64,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8207)
