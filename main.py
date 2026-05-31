"""
Main entry point: Uvicorn server startup.

Configura e inicia o servidor FastAPI.
"""

import logging
import os
from logging.config import dictConfig

from src.api.app import criar_app

# ===== LOGGING SETUP =====

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "access": {
            "format": "%(asctime)s - %(message)s"
        }
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler"
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler"
        }
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO"
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False
        }
    }
}

dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)


# ===== CONFIGURATION =====

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/webposto"
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

WEBPOSTO_URL = os.getenv("WEBPOSTO_URL")
WEBPOSTO_API_KEY = os.getenv("WEBPOSTO_API_KEY")

# ===== APP CREATION =====

try:
    app = criar_app(
        database_url=DATABASE_URL,
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        webposto_url=WEBPOSTO_URL,
        webposto_api_key=WEBPOSTO_API_KEY,
    )
except Exception as e:
    logger.error(f"Erro ao criar app: {e}", exc_info=True)
    raise


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_config=LOG_CONFIG
    )
