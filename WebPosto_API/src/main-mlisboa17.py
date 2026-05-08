"""
Main Application - WebPosto API
FastAPI Application with integrated auditoria routes
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.webposto.client import WebPostoClient
from src.interfaces.http.routes import (
    auditoria,
    clientes,
