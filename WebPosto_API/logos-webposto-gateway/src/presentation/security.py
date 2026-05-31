import os
from typing import Annotated, Optional

from fastapi import Header, HTTPException


def require_consumer_token(
    x_consumer_token: Annotated[Optional[str], Header(alias="X-Consumer-Token")] = None,
) -> None:
    consumer_token = os.getenv("CONSUMER_TOKEN", "dev-consumer-token")
    if not x_consumer_token or x_consumer_token != consumer_token:
        raise HTTPException(status_code=401, detail="consumer_unauthorized")


def require_admin_token(
    x_admin_token: Annotated[Optional[str], Header(alias="X-Admin-Token")] = None,
) -> None:
    admin_token = os.getenv("ADMIN_TOKEN", "dev-admin-token")
    if not x_admin_token or x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="admin_unauthorized")
