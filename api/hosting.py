"""Hosted Agents API endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from typing import Optional
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from config import settings
from core.code_validator import validate as validate_code
from core.deployer import AgentDeployer, _function_name
from db import get_db, async_session
from models.agent import Agent, AgentSkill
from models.hosted_agent import HostedAgent
from models.rating import AgentStats
from models.user import User
from decimal import Decimal
from models.credit import CreditAccount
from schemas.hosting import (
    HostedAgentCreate, HostedAgentResponse, EnvVarsUpdate,
    CodeUploadResponse, HostedAgentLogsResponse, LogEntry,
)
from utils.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError as AppValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["hosting"])


def _require_hosting_enabled():
    if not settings.HOSTING_ENABLED:
        raise HTTPException(status_code=503, detail="Hosted agents feature is disabled")


async def _get_agent_and_check_owner(agent_id: UUID, user: User, db: AsyncSession) -> Agent:
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    if agent.owner_id != user.id:
        raise ForbiddenError("Not your agent")
    return agent


@router.post("/host", response_model=HostedAgentResponse, status_code=201)
async def create_hosted_agent_json(
    data: HostedAgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a hosted agent (JSON, no file). Upload code later via PUT /{id}/code."""
    _require_hosting_enabled()
    return await _create_hosted_agent(data.name, data.slug, data.description, data.skills,
        data.price_per_task, data.runtime, data.memory_mb, data.timeout_sec, None, user, db)


@router.post("/host/deploy", status_code=201)
async def create_hosted_agent_with_code(
    request: Request,
    file: UploadFile = File(...),
    # --- metadata as JSON part (preferred) ---
    metadata: Optional[str] = Form(None),
    # --- legacy individual form fields (still supported) ---
    name: Optional[str] = Form(None), slug: Optional[str] = Form(None),
    description: str = Form(""),
    skills: Optional[str] = Form(None),  # comma-separated or JSON array
    price_per_task: float = Form(0), runtime: str = Form("python3.12"),
    memory_mb: int = Form(256), timeout_sec: int = Form(60),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create + upload + deploy a hosted agent in one call.

    Accepts either:
      - A `metadata` JSON field with all config (name, slug, skills, env_vars, etc.)
      - Individual form fields (legacy, still works)
    """
    _require_hosting_enabled()
    import json as _json

    env_vars: dict[str, str] = {}

    if metadata:
        try:
            meta = _json.loads(metadata)
        except _json.JSONDecodeError:
            raise AppValidationError("metadata must be valid JSON")
        _name = meta.get("name") or name
        _slug = meta.get("slug") or slug
        _desc = meta.get("description", description)
        raw_skills = meta.get("skills", skills)
        _price = Decimal(str(meta.get("price_per_task", price_per_task)))
        _runtime = meta.get("runtime", runtime)
        _mem = meta.get("memory_mb", memory_mb)
        _timeout = meta.get("timeout_sec", timeout_sec)
        env_vars = meta.get("env_vars", {})
    else:
        _name = name
        _slug = slug
        _desc = description
        raw_skills = skills
        _price = Decimal(str(price_per_task))
        _runtime = runtime
        _mem = memory_mb
        _timeout = timeout_sec

    if not _name or not _slug:
        raise AppValidationError("name and slug are required")
    if not raw_skills:
        raise AppValidationError("skills are required")

    # Parse skills
    if isinstance(raw_skills, list):
        _skills = raw_skills
    elif isinstance(raw_skills, str):
        try:
            _skills = _json.loads(raw_skills) if raw_skills.startswith("[") else [s.strip() for s in raw_skills.split(",") if s.strip()]
        except Exception:
            _skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    else:
        _skills = []

    zip_bytes = await file.read()
    return await _create_hosted_agent(_name, _slug, _desc, _skills,
        _price, _runtime, _mem, _timeout, zip_bytes, user, db, env_vars=env_vars)


async def _create_hosted_agent(
    _name, _slug, _desc, _skills, _price, _runtime, _mem, _timeout, zip_bytes, user, db,
    *, env_vars: dict[str, str] | None = None,
):

    if not _skills:
        raise AppValidationError("At least one skill is required")

    # Validate memory tier
    ALLOWED_MEMORY = [128, 256]
    if _mem not in ALLOWED_MEMORY:
        raise AppValidationError(f"Memory must be one of {ALLOWED_MEMORY}. 512 MB and 1024 MB coming soon.")

    existing = (await db.execute(select(Agent).where(Agent.slug == _slug))).scalar_one_or_none()
    if existing:
        raise ConflictError("Slug already taken")

    # If file provided, validate FIRST before creating anything
    validation = None
    if zip_bytes:
        from core.code_validator import validate
        validation = validate(zip_bytes)
        if not validation.valid:
            raise HTTPException(status_code=422, detail={"errors": validation.errors, "warnings": validation.warnings})

    agent = Agent(
        owner_id=user.id, name=_name, slug=_slug, description=_desc,
        endpoint_type="hosted", pricing_model="per_task", price_per_task=_price,
        currency="credits", health_check_url="hosted://lambda", protocols=["hosted"], status="pending",
    )
    db.add(agent)
    await db.flush()

    for skill_tag in _skills:
        tag = skill_tag if isinstance(skill_tag, str) else skill_tag.get("skill_tag", str(skill_tag))
        db.add(AgentSkill(agent_id=agent.id, skill_tag=tag, category="general", proficiency=0.5))

    db.add(AgentStats(agent_id=agent.id))

    hosted = HostedAgent(
        agent_id=agent.id, runtime=_runtime, memory_mb=_mem,
        timeout_sec=_timeout, deploy_status="pending",
    )
    db.add(hosted)
    await db.commit()
    await db.refresh(hosted)

    # If file provided, deploy immediately
    if zip_bytes:
        deployer = AgentDeployer()
        try:
            agent_json = validation.agent_json or {}
            deploy_env = {"RAA_AGENT_ID": str(agent.id)}
            if env_vars:
                deploy_env.update(env_vars)
            lambda_arn, s3_key = await deployer.build_and_deploy(
                agent.id, zip_bytes, agent_json, deploy_env,
            )
            hosted.lambda_arn = lambda_arn
            hosted.s3_code_key = s3_key
            hosted.deploy_status = "live"
            hosted.code_version = 1
            hosted.code_size_bytes = len(zip_bytes)
            if env_vars:
                hosted.env_vars_keys = list(env_vars.keys())
            agent.status = "online"
            agent.health_status = "healthy"
            agent.endpoint_url = f"https://host.rentaiagent.io/agents/{agent.id}"
            agent.health_check_url = f"https://api.rentaiagent.io/v1/agents/{agent.slug}/health"
            await db.commit()
            await db.refresh(hosted)

            # Auto-embed for RAG
            try:
                from core.embeddings import embed_and_store_agent
                asyncio.create_task(embed_and_store_agent(db, agent))
            except Exception:
                pass
        except Exception as e:
            hosted.deploy_status = "failed"
            hosted.deploy_error = str(e)
            await db.commit()
            await db.refresh(hosted)

    return HostedAgentResponse.model_validate(hosted)


@router.put("/{agent_id}/code", response_model=CodeUploadResponse)
async def upload_code(
    agent_id: UUID, file: UploadFile = File(...),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()
    agent = await _get_agent_and_check_owner(agent_id, user, db)

    hosted = (await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent_id))).scalar_one_or_none()
    if not hosted:
        raise NotFoundError("Agent is not registered for hosting. Call POST /host first.")
    if hosted.deploy_status == "building":
        raise AppValidationError("A deployment is already in progress")

    zip_bytes = await file.read()
    result = validate_code(zip_bytes)
    if not result.valid:
        raise HTTPException(status_code=422, detail={"errors": result.errors, "warnings": result.warnings})

    hosted.deploy_status = "building"
    hosted.deploy_error = None
    await db.flush()

    try:
        deployer = AgentDeployer()
        arn, s3_key = await deployer.build_and_deploy(agent_id, zip_bytes, result.agent_json, {})
        hosted.lambda_arn = arn
        hosted.s3_code_key = s3_key
        hosted.code_version += 1
        hosted.code_size_bytes = len(zip_bytes)
        hosted.deploy_status = "live"
        hosted.deploy_error = None
        agent.status = "online"
        agent.health_status = "healthy"
    except Exception as e:
        logger.exception("Deploy failed for agent %s", agent_id)
        hosted.deploy_status = "failed"
        hosted.deploy_error = str(e)

    await db.commit()
    await db.refresh(hosted)

    asyncio.create_task(_embed_agent_background(str(agent_id)))

    return CodeUploadResponse(
        version=hosted.code_version, deploy_status=hosted.deploy_status,
        message="Deployed successfully" if hosted.deploy_status == "live" else f"Deploy failed: {hosted.deploy_error}",
    )


async def _embed_agent_background(agent_id: str):
    try:
        from core.embeddings import embed_and_store_agent
        async with async_session() as session:
            agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
            if agent:
                await embed_and_store_agent(session, agent)
                await session.commit()
    except Exception as e:
        logger.error("Background embed failed for agent %s: %s", agent_id, e)


@router.put("/{agent_id}/env")
async def update_env_vars(
    agent_id: UUID, data: EnvVarsUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()
    await _get_agent_and_check_owner(agent_id, user, db)
    hosted = (await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent_id))).scalar_one_or_none()
    if not hosted:
        raise NotFoundError("Agent is not hosted")

    deployer = AgentDeployer()
    if hosted.lambda_arn:
        await deployer.update_env(hosted.lambda_arn, data.env_vars)
    hosted.env_vars_keys = list(data.env_vars.keys())
    await db.commit()
    return {"message": "Environment variables updated", "keys": hosted.env_vars_keys}


@router.post("/{agent_id}/start")
async def start_agent(
    agent_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()
    agent = await _get_agent_and_check_owner(agent_id, user, db)
    hosted = (await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent_id))).scalar_one_or_none()
    if not hosted:
        raise NotFoundError("Agent is not hosted")
    if hosted.deploy_status not in ("live", "stopped"):
        raise AppValidationError(f"Cannot start agent in '{hosted.deploy_status}' state. Upload code first.")

    deployer = AgentDeployer()
    await deployer.start(agent_id)
    hosted.deploy_status = "live"
    agent.status = "online"
    await db.commit()
    return {"message": "Agent started"}


@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()
    agent = await _get_agent_and_check_owner(agent_id, user, db)
    hosted = (await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent_id))).scalar_one_or_none()
    if not hosted:
        raise NotFoundError("Agent is not hosted")

    deployer = AgentDeployer()
    await deployer.stop(agent_id)
    hosted.deploy_status = "stopped"
    agent.status = "offline"
    await db.commit()
    return {"message": "Agent stopped"}


@router.get("/{agent_id}/logs", response_model=HostedAgentLogsResponse)
async def get_logs(
    agent_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()
    await _get_agent_and_check_owner(agent_id, user, db)
    hosted = (await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent_id))).scalar_one_or_none()
    if not hosted:
        raise NotFoundError("Agent is not hosted")

    func_name = _function_name(agent_id)
    deployer = AgentDeployer()
    raw_logs = await deployer.get_logs(func_name)
    return HostedAgentLogsResponse(
        logs=[LogEntry(timestamp=l.get("timestamp"), message=l.get("message", "")) for l in raw_logs],
        function_name=func_name,
    )


@router.get("/{agent_id}/hosting", response_model=HostedAgentResponse)
async def get_hosting_info(
    agent_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()
    await _get_agent_and_check_owner(agent_id, user, db)
    hosted = (await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent_id))).scalar_one_or_none()
    if not hosted:
        raise NotFoundError("Agent is not hosted")
    return hosted


@router.delete("/{agent_id}/hosting")
async def delete_hosting(
    agent_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()
    agent = await _get_agent_and_check_owner(agent_id, user, db)
    hosted = (await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent_id))).scalar_one_or_none()
    if not hosted:
        raise NotFoundError("Agent is not hosted")

    deployer = AgentDeployer()
    await deployer.delete(agent_id)
    await db.delete(hosted)
    agent.status = "offline"
    agent.endpoint_type = "rest"
    await db.commit()
    return {"message": "Hosting removed and Lambda deleted"}


@router.post("/{agent_ref}/execute")
async def execute_agent(
    agent_ref: str, payload: dict,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _require_hosting_enabled()

    # Accept both UUID and slug
    try:
        agent_uuid = UUID(agent_ref)
        agent = (await db.execute(select(Agent).where(Agent.id == agent_uuid))).scalar_one_or_none()
    except (ValueError, AttributeError):
        agent = (await db.execute(select(Agent).where(Agent.slug == agent_ref))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")

    hosted = (await db.execute(
        select(HostedAgent).where(HostedAgent.agent_id == agent.id, HostedAgent.deploy_status == "live")
    )).scalar_one_or_none()
    if not hosted:
        raise AppValidationError("Agent is not hosted or not live")

    is_owner = agent.owner_id == user.id
    platform_fee = Decimal("0")

    if not is_owner:
        price = agent.price_per_task
        credit_account = (await db.execute(
            select(CreditAccount).where(CreditAccount.user_id == user.id)
        )).scalar_one_or_none()
        if not credit_account or credit_account.balance < price:
            raise AppValidationError(f"Insufficient credits. Need {float(price)}, have {float(credit_account.balance) if credit_account else 0}")

        # Deduct credits directly (no task/escrow for direct execute)
        platform_fee = price * Decimal("0.15")
        credit_account.balance -= price
        await db.flush()

    deployer = AgentDeployer()
        # Build task payload matching what handler.handle(task) expects
    # task.get("payload") should give the user's data directly
    invoke_payload = {
        "id": str(agent.id),
        "skill": payload.pop("skill", "default") if isinstance(payload, dict) else "default",
        "payload": payload,
    }

    try:
        result = await deployer.invoke(hosted.lambda_arn, invoke_payload)
    except Exception as e:
        if not is_owner:
            # Refund on failure
            credit_account.balance += price
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Agent invocation failed: {e}")

    hosted.invocation_count += 1
    hosted.last_invoked_at = datetime.now(timezone.utc)

    if not is_owner:
        if result.get("status") == "completed":
            # Pay the provider
            provider_account = (await db.execute(
                select(CreditAccount).where(CreditAccount.user_id == agent.owner_id)
            )).scalar_one_or_none()
            if provider_account:
                provider_account.balance += (price - platform_fee)
        else:
            # Refund on failure
            credit_account.balance += price

    await db.commit()
    return result
