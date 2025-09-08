from openai import AsyncOpenAI
from pydantic_settings import BaseSettings
from pydantic import Extra

class Settings(BaseSettings):
    openai_api_key: str
    model_name: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        extra = Extra.allow
        env_file_encoding = "utf-8"

_settings = None
_client = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client
