"""Register all 15 worker agents via the RentAnAgent API."""
import httpx
import sys

BASE = "http://127.0.0.1:8100"

AGENTS = [
    {
        "name": "Text Summarizer",
        "slug": "text-summarizer",
        "description": "Summarizes text and extracts keywords using NLP techniques.",
        "endpoint_url": "http://127.0.0.1:8201/handle",
        "endpoint_type": "rest",
        "price_per_task": "3.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8201/health",
        "version": "1.0.0",
        "framework": "fastapi",
        "skills": [
            {"skill_tag": "summarize", "category": "nlp", "proficiency": 0.8},
            {"skill_tag": "extract-keywords", "category": "nlp", "proficiency": 0.8},
        ],
    },
    {
        "name": "Data Transformer",
        "slug": "data-transformer",
        "description": "Transforms data between JSON, CSV, and other formats.",
        "endpoint_url": "http://127.0.0.1:8202/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8202/health",
        "version": "1.0.0",
        "framework": "fastapi",
        "skills": [
            {"skill_tag": "json-to-csv", "category": "data", "proficiency": 0.9},
            {"skill_tag": "csv-to-json", "category": "data", "proficiency": 0.9},
            {"skill_tag": "format-json", "category": "data", "proficiency": 0.9},
        ],
    },
    {
        "name": "Code Analyzer",
        "slug": "code-analyzer",
        "description": "Analyzes source code: line counts, language detection, function extraction.",
        "endpoint_url": "http://127.0.0.1:8203/handle",
        "endpoint_type": "rest",
        "price_per_task": "5.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8203/health",
        "version": "1.0.0",
        "framework": "fastapi",
        "skills": [
            {"skill_tag": "count-lines", "category": "code", "proficiency": 0.9},
            {"skill_tag": "detect-language", "category": "code", "proficiency": 0.85},
            {"skill_tag": "find-functions", "category": "code", "proficiency": 0.85},
        ],
    },
    {
        "name": "Sentiment Analyzer",
        "slug": "sentiment-analyzer",
        "description": "Analyzes text sentiment and detects emotions using lexicon-based NLP.",
        "endpoint_url": "http://127.0.0.1:8204/handle",
        "endpoint_type": "rest",
        "price_per_task": "3.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8204/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "analyze-sentiment", "category": "nlp", "proficiency": 0.8},
            {"skill_tag": "detect-emotion", "category": "nlp", "proficiency": 0.75},
        ],
    },
    {
        "name": "Text Translator",
        "slug": "text-translator",
        "description": "Detects languages and transliterates text between Roman and Devanagari scripts.",
        "endpoint_url": "http://127.0.0.1:8205/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8205/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "detect-language", "category": "nlp", "proficiency": 0.8},
            {"skill_tag": "transliterate", "category": "nlp", "proficiency": 0.7},
        ],
    },
    {
        "name": "Email Writer",
        "slug": "email-writer",
        "description": "Generates professional, casual, and follow-up emails from templates. Improves text style.",
        "endpoint_url": "http://127.0.0.1:8206/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8206/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "write-email", "category": "text", "proficiency": 0.85},
            {"skill_tag": "improve-text", "category": "text", "proficiency": 0.8},
        ],
    },
    {
        "name": "Hash Generator",
        "slug": "hash-generator",
        "description": "Generates hashes (MD5, SHA256, SHA512), UUIDs, and base64 encoding/decoding.",
        "endpoint_url": "http://127.0.0.1:8207/handle",
        "endpoint_type": "rest",
        "price_per_task": "1.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8207/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "hash-text", "category": "utility", "proficiency": 0.95},
            {"skill_tag": "generate-uuid", "category": "utility", "proficiency": 0.95},
            {"skill_tag": "encode-base64", "category": "utility", "proficiency": 0.95},
        ],
    },
    {
        "name": "JSON Validator",
        "slug": "json-validator",
        "description": "Validates JSON, computes diffs between JSON objects, and flattens nested structures.",
        "endpoint_url": "http://127.0.0.1:8208/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8208/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "validate-json", "category": "data", "proficiency": 0.9},
            {"skill_tag": "json-diff", "category": "data", "proficiency": 0.85},
            {"skill_tag": "flatten-json", "category": "data", "proficiency": 0.9},
        ],
    },
    {
        "name": "Regex Helper",
        "slug": "regex-helper",
        "description": "Tests regex patterns, extracts matches, and generates common regex patterns.",
        "endpoint_url": "http://127.0.0.1:8209/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8209/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "test-regex", "category": "code", "proficiency": 0.9},
            {"skill_tag": "extract-matches", "category": "code", "proficiency": 0.9},
            {"skill_tag": "generate-regex", "category": "code", "proficiency": 0.8},
        ],
    },
    {
        "name": "Markdown Converter",
        "slug": "markdown-converter",
        "description": "Converts between Markdown and HTML, and formats/prettifies Markdown text.",
        "endpoint_url": "http://127.0.0.1:8210/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8210/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "md-to-html", "category": "text", "proficiency": 0.9},
            {"skill_tag": "html-to-md", "category": "text", "proficiency": 0.85},
            {"skill_tag": "format-markdown", "category": "text", "proficiency": 0.85},
        ],
    },
    {
        "name": "API Tester",
        "slug": "api-tester",
        "description": "Makes HTTP requests and checks endpoint health, status, and SSL validity.",
        "endpoint_url": "http://127.0.0.1:8211/handle",
        "endpoint_type": "rest",
        "price_per_task": "3.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8211/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "http-request", "category": "devops", "proficiency": 0.9},
            {"skill_tag": "check-endpoint", "category": "devops", "proficiency": 0.85},
        ],
    },
    {
        "name": "Diff Tool",
        "slug": "diff-tool",
        "description": "Computes text diffs, word counts, and character statistics.",
        "endpoint_url": "http://127.0.0.1:8212/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8212/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "text-diff", "category": "text", "proficiency": 0.9},
            {"skill_tag": "word-count", "category": "text", "proficiency": 0.95},
            {"skill_tag": "char-stats", "category": "text", "proficiency": 0.95},
        ],
    },
    {
        "name": "Math Solver",
        "slug": "math-solver",
        "description": "Evaluates math expressions safely, converts units, and computes statistics.",
        "endpoint_url": "http://127.0.0.1:8213/handle",
        "endpoint_type": "rest",
        "price_per_task": "3.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8213/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "evaluate-expression", "category": "math", "proficiency": 0.9},
            {"skill_tag": "unit-convert", "category": "math", "proficiency": 0.85},
            {"skill_tag": "statistics", "category": "math", "proficiency": 0.9},
        ],
    },
    {
        "name": "Date Calculator",
        "slug": "date-calculator",
        "description": "Calculates date differences, adds time periods, and formats dates.",
        "endpoint_url": "http://127.0.0.1:8214/handle",
        "endpoint_type": "rest",
        "price_per_task": "2.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8214/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "date-diff", "category": "utility", "proficiency": 0.9},
            {"skill_tag": "add-to-date", "category": "utility", "proficiency": 0.9},
            {"skill_tag": "format-date", "category": "utility", "proficiency": 0.9},
        ],
    },
    {
        "name": "Password Generator",
        "slug": "password-generator",
        "description": "Generates secure passwords and passphrases, checks password strength.",
        "endpoint_url": "http://127.0.0.1:8215/handle",
        "endpoint_type": "rest",
        "price_per_task": "1.0000",
        "currency": "INR",
        "health_check_url": "http://127.0.0.1:8215/health",
        "version": "1.0.0",
        "framework": "custom",
        "skills": [
            {"skill_tag": "generate-password", "category": "security", "proficiency": 0.9},
            {"skill_tag": "check-strength", "category": "security", "proficiency": 0.85},
            {"skill_tag": "generate-passphrase", "category": "security", "proficiency": 0.9},
        ],
    },
]


def main():
    client = httpx.Client(base_url=BASE, timeout=30)
    
    # Login
    r = client.post("/v1/auth/login", json={"email": "rk@test.com", "password": "test1234"})
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Logged in as rk@test.com")

    agent_ids = []
    for agent_data in AGENTS:
        slug = agent_data["slug"]
        # Try to get existing
        r = client.get(f"/v1/agents/{slug}")
        if r.status_code == 200:
            # Update
            existing = r.json()
            agent_id = existing["id"]
            update = {k: v for k, v in agent_data.items() if k != "slug"}
            r = client.patch(f"/v1/agents/{slug}", json=update, headers=headers)
            if r.status_code == 200:
                print(f"✓ Updated {slug} ({agent_id})")
            else:
                print(f"✗ Update {slug} failed: {r.status_code} {r.text}")
        else:
            # Create
            r = client.post("/v1/agents", json=agent_data, headers=headers)
            if r.status_code == 201:
                agent_id = r.json()["id"]
                print(f"✓ Created {slug} ({agent_id})")
            else:
                print(f"✗ Create {slug} failed: {r.status_code} {r.text}")
                continue
        agent_ids.append(agent_id)

    # Approve all agents (admin endpoint)
    for aid in agent_ids:
        r = client.post(f"/v1/admin/agents/{aid}/approve", headers=headers)
        if r.status_code == 200:
            print(f"✓ Approved {aid}")
        else:
            print(f"  Approve {aid}: {r.status_code} {r.text}")

    print(f"\nAll {len(agent_ids)} agents registered and approved.")


if __name__ == "__main__":
    main()
