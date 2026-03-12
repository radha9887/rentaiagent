"""Math Solver Agent - Port 8213"""
import ast
import operator
import math
import statistics as stats_lib
from base_worker import create_worker_app

SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        op = SAFE_OPS.get(type(node.op))
        if not op:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand)
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


UNIT_CONVERSIONS = {
    ("km", "miles"): (0.621371, "{value} × 0.621371"),
    ("miles", "km"): (1.60934, "{value} × 1.60934"),
    ("kg", "lbs"): (2.20462, "{value} × 2.20462"),
    ("lbs", "kg"): (0.453592, "{value} × 0.453592"),
    ("celsius", "fahrenheit"): (None, "({value} × 9/5) + 32"),
    ("fahrenheit", "celsius"): (None, "({value} - 32) × 5/9"),
    ("m", "ft"): (3.28084, "{value} × 3.28084"),
    ("ft", "m"): (0.3048, "{value} × 0.3048"),
    ("cm", "inches"): (0.393701, "{value} × 0.393701"),
    ("inches", "cm"): (2.54, "{value} × 2.54"),
    ("liters", "gallons"): (0.264172, "{value} × 0.264172"),
    ("gallons", "liters"): (3.78541, "{value} × 3.78541"),
}


def evaluate_expression(payload: dict) -> dict:
    expr = payload.get("expression", "")
    if not expr:
        raise ValueError("No expression provided")
    tree = ast.parse(expr, mode="eval")
    result = _safe_eval(tree.body)
    return {"result": result, "expression": expr, "steps": [f"{expr} = {result}"]}


def unit_convert(payload: dict) -> dict:
    value = payload.get("value", 0)
    from_unit = payload.get("from", "").lower()
    to_unit = payload.get("to", "").lower()
    key = (from_unit, to_unit)
    if key not in UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported conversion: {from_unit} → {to_unit}")
    factor, formula = UNIT_CONVERSIONS[key]
    if from_unit == "celsius" and to_unit == "fahrenheit":
        result = value * 9 / 5 + 32
    elif from_unit == "fahrenheit" and to_unit == "celsius":
        result = (value - 32) * 5 / 9
    else:
        result = value * factor
    return {"result": round(result, 6), "formula": formula.format(value=value), "from": from_unit, "to": to_unit}


def compute_statistics(payload: dict) -> dict:
    numbers = payload.get("numbers", [])
    if not numbers:
        raise ValueError("No numbers provided")
    try:
        mode = stats_lib.mode(numbers)
    except stats_lib.StatisticsError:
        mode = None
    return {
        "mean": round(stats_lib.mean(numbers), 4),
        "median": stats_lib.median(numbers),
        "mode": mode,
        "std_dev": round(stats_lib.stdev(numbers), 4) if len(numbers) > 1 else 0,
        "min": min(numbers), "max": max(numbers),
        "sum": sum(numbers), "count": len(numbers),
    }


app = create_worker_app("math-solver", {
    "evaluate-expression": evaluate_expression,
    "unit-convert": unit_convert,
    "statistics": compute_statistics,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8213)
