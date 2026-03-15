"""Lambda deployer for hosted agents."""

import asyncio
import io
import json
import logging
import time
import zipfile
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)

WRAPPER_PY = """import json
import time
import traceback

def lambda_handler(event, context):
    if isinstance(event, dict) and event.get("type") == "health":
        return {"status": "healthy", "timestamp": time.time()}
    if isinstance(event, dict) and event.get("jsonrpc") == "2.0":
        task_data = event.get("params", {})
    else:
        task_data = event
    start = time.time()
    try:
        from handler import handle
        result = handle(task_data)
        duration_ms = (time.time() - start) * 1000
        return {"status": "completed", "data": result, "duration_ms": round(duration_ms, 2)}
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return {"status": "failed", "error": str(e), "traceback": traceback.format_exc(), "duration_ms": round(duration_ms, 2)}
"""


def _function_name(agent_id) -> str:
    return f"raa-agent-{str(agent_id)[:8]}"


class AgentDeployer:
    def __init__(self):
        self._simulation = settings.SIMULATION_MODE
        if not self._simulation:
            import boto3
            self.lambda_client = boto3.client("lambda", region_name="ap-south-1")
            self.s3_client = boto3.client("s3", region_name="ap-south-1")
        self.bucket = settings.AGENT_CODE_BUCKET
        self.role_arn = settings.LAMBDA_ROLE_ARN

    async def build_and_deploy(self, agent_id, zip_bytes: bytes, agent_json: dict, env_vars: dict | None = None):
        func_name = _function_name(agent_id)
        s3_key = f"agents/{agent_id}/code.zip"

        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, "a") as zf:
            zf.writestr("wrapper.py", WRAPPER_PY)
        final_zip = buf.getvalue()

        if self._simulation:
            logger.info("[SIM] deploy %s -> s3://%s/%s", func_name, self.bucket, s3_key)
            return f"arn:aws:lambda:ap-south-1:000000000000:function:{func_name}", s3_key

        def _deploy():
            self.s3_client.put_object(Bucket=self.bucket, Key=s3_key, Body=final_zip)
            env = {"Variables": env_vars or {}}
            try:
                resp = self.lambda_client.create_function(
                    FunctionName=func_name, Runtime=agent_json.get("runtime", "python3.12"),
                    Role=self.role_arn, Handler="wrapper.lambda_handler",
                    Code={"S3Bucket": self.bucket, "S3Key": s3_key},
                    MemorySize=agent_json.get("memory_mb", 256),
                    Timeout=agent_json.get("timeout_sec", 60), Environment=env,
                )
                return resp["FunctionArn"]
            except self.lambda_client.exceptions.ResourceConflictException:
                self.lambda_client.update_function_code(FunctionName=func_name, S3Bucket=self.bucket, S3Key=s3_key)
                self.lambda_client.update_function_configuration(
                    FunctionName=func_name, Runtime=agent_json.get("runtime", "python3.12"),
                    Handler="wrapper.lambda_handler", MemorySize=agent_json.get("memory_mb", 256),
                    Timeout=agent_json.get("timeout_sec", 60), Environment=env,
                )
                resp = self.lambda_client.get_function(FunctionName=func_name)
                return resp["Configuration"]["FunctionArn"]

        arn = await asyncio.to_thread(_deploy)
        return arn, s3_key

    async def start(self, agent_id):
        func_name = _function_name(agent_id)
        if self._simulation:
            logger.info("[SIM] start %s", func_name)
            return
        await asyncio.to_thread(self.lambda_client.delete_function_concurrency, FunctionName=func_name)

    async def stop(self, agent_id):
        func_name = _function_name(agent_id)
        if self._simulation:
            logger.info("[SIM] stop %s", func_name)
            return
        await asyncio.to_thread(
            self.lambda_client.put_function_concurrency,
            FunctionName=func_name, ReservedConcurrentExecutions=0,
        )

    async def invoke(self, lambda_arn: str, payload: dict) -> dict:
        if self._simulation:
            logger.info("[SIM] invoke %s", lambda_arn)
            return {"status": "completed", "data": {"simulated": True, "message": "Hosted agent invocation (simulation)"}, "duration_ms": 42.0}

        def _invoke():
            resp = self.lambda_client.invoke(FunctionName=lambda_arn, InvocationType="RequestResponse", Payload=json.dumps(payload))
            return json.loads(resp["Payload"].read())

        return await asyncio.to_thread(_invoke)

    async def update_env(self, lambda_arn: str, env_vars: dict):
        if self._simulation:
            logger.info("[SIM] update_env %s", lambda_arn)
            return
        await asyncio.to_thread(
            self.lambda_client.update_function_configuration,
            FunctionName=lambda_arn, Environment={"Variables": env_vars},
        )

    async def get_logs(self, function_name: str, hours: int = 24, limit: int = 100) -> list[dict]:
        if self._simulation:
            return [{"timestamp": datetime.now(timezone.utc).isoformat(), "message": "[SIM] No logs in simulation mode"}]

        import boto3
        logs_client = boto3.client("logs", region_name="ap-south-1")
        log_group = f"/aws/lambda/{function_name}"
        start_time = int((time.time() - hours * 3600) * 1000)

        def _fetch():
            try:
                resp = logs_client.filter_log_events(logGroupName=log_group, startTime=start_time, limit=limit, interleaved=True)
                return [{"timestamp": e.get("timestamp"), "message": e.get("message", "")} for e in resp.get("events", [])]
            except Exception as e:
                logger.error("Failed to fetch logs for %s: %s", log_group, e)
                return []

        return await asyncio.to_thread(_fetch)

    async def delete(self, agent_id):
        func_name = _function_name(agent_id)
        s3_key = f"agents/{agent_id}/code.zip"
        if self._simulation:
            logger.info("[SIM] delete %s", func_name)
            return

        def _delete():
            try:
                self.lambda_client.delete_function(FunctionName=func_name)
            except Exception:
                pass
            try:
                self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            except Exception:
                pass

        await asyncio.to_thread(_delete)
