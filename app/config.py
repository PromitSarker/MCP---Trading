from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, BaseModel, Extra
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import os
class Settings(BaseSettings):
    groq_api_key: str = Field(default="")
    model_name: str = Field()
    groq_api_url: str = Field()
    request_timeout: int = Field(default=120)  # 2 minutes timeout

    mongo_uri: str = Field(default=os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db_name: str = Field(default="business_planner")

    class Config:
        env_file = ".env"
        extra = Extra.allow

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
        # Truncate long messages to prevent payload size issues
        truncated_messages = []
        for msg in messages:
            content = msg['content']
            if len(content) > 8000:  # Truncate long messages
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
                        "max_tokens": min(kwargs.get("max_tokens", 9000), 9000),  # Limit max tokens
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
def get_settings() -> Settings:
    return Settings()

@lru_cache
def get_groq_client() -> GroqClient:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("Missing GROQ_API_KEY in environment or .env file")
    return GroqClient(api_key=settings.groq_api_key, api_url=settings.groq_api_url)