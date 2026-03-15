from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rentanagent"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = ""  # Required: set via RAA_JWT_SECRET env var
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    PLATFORM_FEE_PERCENT: float = 15.0
    APP_NAME: str = "RentAiAgent"
    DEBUG: bool = False
    HMAC_SECRET: str = ""  # Required: set via RAA_HMAC_SECRET env var
    HEALTH_CHECK_TIMEOUT_SECONDS: int = 10
    SIMULATION_MODE: bool = True
    MAX_CHAIN_DEPTH: int = 5
    MAX_CHAIN_BREADTH: int = 10
    WEBHOOK_TIMEOUT_SECONDS: int = 30
    WEBHOOK_MAX_RETRIES: int = 3
    EXTERNAL_AGENT_HEALTH_INTERVAL_MINUTES: int = 60
    HEALTH_CHECK_INTERVAL_SECONDS: int = 300
    MAX_CONSECUTIVE_HEALTH_FAILS: int = 3
    DEFAULT_MAX_CONCURRENT_TASKS: int = 10
    OPENAI_API_KEY: str = ""
    LAMBDA_ROLE_ARN: str = ""
    AGENT_CODE_BUCKET: str = "rentaiagent-agent-code"
    HOSTING_ENABLED: bool = True

    model_config = {"env_prefix": "RAA_", "env_file": ".env"}


settings = Settings()
