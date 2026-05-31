from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import metrics_api, tax_api


def create_app() -> FastAPI:
    app = FastAPI(title='WebPosto API')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.include_router(metrics_api.router)
    app.include_router(tax_api.router)

    return app


app = create_app()
