"""JSON Validator Agent - Port 8208"""
import json
from base_worker import create_worker_app


def _depth(obj, d=0):
    if isinstance(obj, dict):
        return max((_depth(v, d + 1) for v in obj.values()), default=d)
    if isinstance(obj, list):
        return max((_depth(v, d + 1) for v in obj), default=d)
    return d


def _count_keys(obj):
    if isinstance(obj, dict):
        return len(obj) + sum(_count_keys(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_count_keys(v) for v in obj)
    return 0


def validate_json(payload: dict) -> dict:
    json_string = payload.get("json_string", "")
    if not json_string:
        raise ValueError("No json_string provided")
    try:
        parsed = json.loads(json_string)
        return {"valid": True, "error": None, "stats": {"keys": _count_keys(parsed), "depth": _depth(parsed), "size": len(json_string)}}
    except json.JSONDecodeError as e:
        return {"valid": False, "error": str(e), "stats": {"keys": 0, "depth": 0, "size": len(json_string)}}


def json_diff(payload: dict) -> dict:
    a = payload.get("json_a", {})
    b = payload.get("json_b", {})
    if isinstance(a, str): a = json.loads(a)
    if isinstance(b, str): b = json.loads(b)
    keys_a, keys_b = set(a.keys()), set(b.keys())
    added = list(keys_b - keys_a)
    removed = list(keys_a - keys_b)
    changed = [k for k in keys_a & keys_b if a[k] != b[k]]
    return {"added": added, "removed": removed, "changed": changed}


def flatten_json(payload: dict) -> dict:
    data = payload.get("data", payload.get("json", {}))
    if isinstance(data, str): data = json.loads(data)
    flat = {}
    def _flatten(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                _flatten(v, f"{prefix}{k}." if prefix else f"{k}.")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _flatten(v, f"{prefix}{i}.")
        else:
            flat[prefix.rstrip(".")] = obj
    _flatten(data)
    return {"flattened": flat}


app = create_worker_app("json-validator", {
    "validate-json": validate_json,
    "json-diff": json_diff,
    "flatten-json": flatten_json,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8208)
