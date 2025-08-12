from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, Extra
import httpx
import os
from tenacity import retry, stop_after_attempt, wait_exponential

class Settings(BaseSettings):
    groq_api_key: str
    model_name: str
    groq_api_url: str
    request_timeout: int = Field(default=120)
    mongo_uri: str = Field(default="mongodb://localhost:27017")
    db_name: str = Field(default="business_planner")

    class Config:
        env_file = ".env"
        extra = Extra.allow

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"Loaded Settings: groq_api_key={self.groq_api_key}, model_name={self.model_name}, groq_api_url={self.groq_api_url}")

# To get the settings
@lru_cache
def get_settings() -> Settings:
    return Settings()

# Groq Client
class GroqClient:
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = httpx.Timeout(timeout=220.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_chat_completion(self, messages: list, **kwargs):
        truncated_messages = []
        for msg in messages:
            content = msg['content']
            if len(content) > 8000:
                content = content[:8000] + "..."
            truncated_messages.append({"role": msg['role'], "content": content})

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "messages": truncated_messages,
                        "model": kwargs.get("model"),
                        "temperature": kwargs.get("temperature", 0.5),
                        "max_tokens": min(kwargs.get("max_tokens", 9000), 9000),
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 413:
                    raise ValueError("Payload too large. Try reducing the input size.") from e
                raise ValueError(f"HTTP error occurred: {str(e)}") from e
            except Exception as e:
                raise ValueError(f"Request failed: {str(e)}") from e


@lru_cache
def get_groq_client() -> GroqClient:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("Missing GROQ_API_KEY in environment or .env file")
    return GroqClient(api_key=settings.groq_api_key, api_url=settings.groq_api_url)

