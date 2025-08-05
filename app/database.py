from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import get_settings
from app.models import BusinessPlanDoc   # we’ll create this next

_db_client: AsyncIOMotorClient | None = None

async def init_db():
    global _db_client
    settings = get_settings()
    _db_client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(database=_db_client[settings.db_name],
                      document_models=[BusinessPlanDoc])