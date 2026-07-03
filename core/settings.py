from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URL: str
    ACCESS_TOKEN_SECRET_KEY: str
    REFRESH_TOKEN_SECRET_KEY: str
    ALGORITHM: str

    @property
    def DATABASE_URL(self) -> str:
        return self.DB_URL

    class Config:
        env_file = ".env"

settings = Settings()