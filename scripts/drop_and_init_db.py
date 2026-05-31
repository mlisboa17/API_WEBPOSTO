import asyncio
import logging
import json
from src.infrastructure.database import engine
from src.infrastructure.persistence.models import Base

# Structured JSON logger
class JsonConsoleHandler(logging.StreamHandler):
    def emit(self, record):
        log_entry = self.format(record)
        try:
            log_json = json.dumps({
                "level": record.levelname,
                "msg": record.getMessage(),
                "name": record.name,
                "time": self.formatTime(record),
            })
            print(log_json)
        except Exception:
            print(log_entry)

logger = logging.getLogger("drop_and_init_db")
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(JsonConsoleHandler())

async def drop_and_init():
    try:
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("✅ Tabelas removidas!")
            
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Schema criado!")
    except Exception as e:
        logger.error(f"Erro ao drop/init schema: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(drop_and_init())
