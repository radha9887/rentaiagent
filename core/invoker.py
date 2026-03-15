"""Invoke hosted Lambda agents."""

from core.deployer import AgentDeployer


async def invoke_hosted_agent(hosted_agent, task) -> dict:
    """Invoke a hosted Lambda agent and return result dict."""
    deployer = AgentDeployer()
    payload = {
        "id": str(task.id),
        "skill": task.skill_requested,
        "payload": task.payload,
    }
    return await deployer.invoke(hosted_agent.lambda_arn, payload)
