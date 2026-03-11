"""Data Transformer Agent - Port 8202"""
import csv
import io
import json
from base_worker import create_worker_app


def json_to_csv(payload: dict) -> dict:
    data = payload.get("data", [])
    if not data or not isinstance(data, list):
        raise ValueError("Expected 'data' as a list of objects")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return {"csv": output.getvalue(), "rows": len(data)}


def csv_to_json(payload: dict) -> dict:
    raw = payload.get("csv", "")
    if not raw:
        raise ValueError("No csv provided")
    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    return {"data": rows, "rows": len(rows)}


def format_json(payload: dict) -> dict:
    data = payload.get("data")
    if data is None:
        raise ValueError("No data provided")
    formatted = json.dumps(data, indent=2, sort_keys=True)
    return {"formatted": formatted}


app = create_worker_app("data-transformer", {
    "json-to-csv": json_to_csv,
    "csv-to-json": csv_to_json,
    "format-json": format_json,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8202)
