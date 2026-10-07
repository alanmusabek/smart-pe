from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_URL: str
    ACCESS_TOKEN_SECRET_KEY: str
    REFRESH_TOKEN_SECRET_KEY: str
    ALGORITHM: str
    PUBLIC_REGISTRATION_ENABLED: bool = True
    DEMO_MODE: bool = False
    DEMO_TEACHER_PASSWORD: str = ''
    DEMO_STUDENT_PASSWORD: str = ''
    MODEL_RETRAIN_ENABLED: bool = True
    LLM_ENABLED: bool = True
    LLM_BASE_URL: str = 'http://127.0.0.1:11434/v1'
    LLM_API_KEY: str = 'ollama'
    LLM_MODEL: str = 'qwen2.5:0.5b'
    LLM_TIMEOUT: float = Field(default=15, ge=1, le=30)
    LLM_MAX_TOKENS: int = Field(default=200, ge=32, le=1024)
    LLM_TEMPERATURE: float = Field(default=0.4, ge=0, le=2)
    LLM_REASONING_EFFORT: str | None = None

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def DATABASE_URL(self) -> str:
        return self.DB_URL

settings = Settings()
