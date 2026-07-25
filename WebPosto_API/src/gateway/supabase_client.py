"""Bootstrap do cliente Supabase (Postgres) usado pelos repositórios de domínio.

Segue o mesmo padrão "cliente opcional" já usado em AuditLogService/RBACService
(src/services/governance/): se as credenciais não estiverem configuradas, o
cliente é `None` e os chamadores devem cair para um fallback local (ex.: lista
em memória), nunca quebrar em runtime por falta de Supabase.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def get_supabase_client() -> Any | None:
    """Retorna um cliente Supabase singleton, ou None se não configurado.

    Requer as variáveis de ambiente SUPABASE_URL e SUPABASE_KEY (service role
    key, uso interno do backend — nunca expor ao frontend).
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None

    try:
        from supabase import create_client
    except ImportError:
        return None

    return create_client(url, key)
