"""SQL to PySpark converter — translates SQL queries to PySpark DataFrame API code."""

import os
import json
import urllib.request

def handle(task):
    sql = task.get("payload", {}).get("sql", "") or task.get("payload", {}).get("text", "")
    if not sql or not sql.strip():
        return {"error": "Provide a SQL query in the 'sql' field"}

    style = task.get("payload", {}).get("style", "dataframe")  # dataframe or spark_sql

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not configured"}

    prompt = f"""Convert this SQL query to PySpark code.

Style: {"DataFrame API (use .select(), .filter(), .groupBy(), .join() etc.)" if style == "dataframe" else "Spark SQL (use spark.sql())"}

SQL:
```sql
{sql}
```

Return ONLY:
1. The PySpark code (complete, runnable)
2. Brief comments explaining each step
3. Any assumptions about the schema

Do NOT include explanations outside the code block."""

    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a PySpark expert. Convert SQL to clean, production-quality PySpark code. Use DataFrame API by default. Include proper imports."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2000
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            pyspark_code = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {})
            return {
                "pyspark_code": pyspark_code,
                "original_sql": sql,
                "style": style,
                "tokens_used": tokens.get("total_tokens", 0)
            }
    except Exception as e:
        return {"error": f"Conversion failed: {str(e)}"}
