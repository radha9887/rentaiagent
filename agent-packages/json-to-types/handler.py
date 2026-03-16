"""JSON to Types — paste JSON, get Pydantic models, TypeScript interfaces, or JSON Schema."""

import json

def _infer_type(value):
    if value is None:
        return "Optional[Any]", "any", "null"
    if isinstance(value, bool):
        return "bool", "boolean", "boolean"
    if isinstance(value, int):
        return "int", "number", "integer"
    if isinstance(value, float):
        return "float", "number", "number"
    if isinstance(value, str):
        return "str", "string", "string"
    if isinstance(value, list):
        return "list", "array", "array"
    if isinstance(value, dict):
        return "dict", "object", "object"
    return "Any", "any", "any"

def _to_pydantic(data, class_name="Root", indent=0):
    if not isinstance(data, dict):
        return f"# Input is {type(data).__name__}, not an object"
    
    lines = []
    sub_models = []
    pad = "    " * indent
    lines.append(f"{pad}class {class_name}(BaseModel):")
    
    for key, value in data.items():
        py_type, _, _ = _infer_type(value)
        if isinstance(value, dict):
            sub_name = key.title().replace("_", "").replace("-", "")
            sub_models.append(_to_pydantic(value, sub_name, indent))
            lines.append(f"{pad}    {key}: {sub_name}")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            sub_name = key.title().replace("_", "").replace("-", "").rstrip("s") + "Item"
            sub_models.append(_to_pydantic(value[0], sub_name, indent))
            lines.append(f"{pad}    {key}: list[{sub_name}]")
        elif isinstance(value, list) and value:
            inner, _, _ = _infer_type(value[0])
            lines.append(f"{pad}    {key}: list[{inner}]")
        elif isinstance(value, list):
            lines.append(f"{pad}    {key}: list")
        else:
            lines.append(f"{pad}    {key}: {py_type}")
    
    return "\n".join(sub_models + [""] + lines) if sub_models else "\n".join(lines)

def _to_typescript(data, name="Root", indent=0):
    if not isinstance(data, dict):
        return f"// Input is {type(data).__name__}, not an object"
    
    lines = []
    sub_interfaces = []
    pad = "  " * indent
    lines.append(f"{pad}interface {name} {{")
    
    for key, value in data.items():
        _, ts_type, _ = _infer_type(value)
        if isinstance(value, dict):
            sub_name = key[0].upper() + key[1:]
            sub_interfaces.append(_to_typescript(value, sub_name, indent))
            lines.append(f"{pad}  {key}: {sub_name};")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            sub_name = key[0].upper() + key[1:].rstrip("s") + "Item"
            sub_interfaces.append(_to_typescript(value[0], sub_name, indent))
            lines.append(f"{pad}  {key}: {sub_name}[];")
        elif isinstance(value, list) and value:
            _, inner_ts, _ = _infer_type(value[0])
            lines.append(f"{pad}  {key}: {inner_ts}[];")
        elif isinstance(value, list):
            lines.append(f"{pad}  {key}: any[];")
        else:
            lines.append(f"{pad}  {key}: {ts_type};")
    
    lines.append(f"{pad}}}")
    return "\n".join(sub_interfaces + [""] + lines) if sub_interfaces else "\n".join(lines)

def _to_json_schema(data, title="Root"):
    if not isinstance(data, dict):
        return {"type": type(data).__name__}
    
    props = {}
    required = []
    for key, value in data.items():
        _, _, js_type = _infer_type(value)
        if isinstance(value, dict):
            props[key] = _to_json_schema(value, key)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            props[key] = {"type": "array", "items": _to_json_schema(value[0], key)}
        elif isinstance(value, list) and value:
            _, _, inner_js = _infer_type(value[0])
            props[key] = {"type": "array", "items": {"type": inner_js}}
        elif isinstance(value, list):
            props[key] = {"type": "array"}
        else:
            props[key] = {"type": js_type}
        if value is not None:
            required.append(key)
    
    return {"type": "object", "title": title, "properties": props, "required": required}

def handle(task):
    payload = task.get("payload", {})
    json_input = payload.get("json", "") or payload.get("text", "")
    target = payload.get("target", "all")  # pydantic, typescript, jsonschema, all
    class_name = payload.get("class_name", "Root")
    
    if not json_input:
        return {"error": "Provide JSON in the 'json' field"}
    
    if isinstance(json_input, str):
        try:
            data = json.loads(json_input)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {str(e)}"}
    else:
        data = json_input
    
    # Handle list input - use first element
    if isinstance(data, list):
        if not data:
            return {"error": "Empty array"}
        data = data[0]
    
    result = {}
    
    if target in ("pydantic", "all"):
        result["pydantic"] = "from pydantic import BaseModel\nfrom typing import Optional, Any\n\n" + _to_pydantic(data, class_name)
    
    if target in ("typescript", "all"):
        result["typescript"] = _to_typescript(data, class_name)
    
    if target in ("jsonschema", "all"):
        result["json_schema"] = _to_json_schema(data, class_name)
    
    return result
