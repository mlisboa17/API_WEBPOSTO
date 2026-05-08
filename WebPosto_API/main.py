"""
Ponto de entrada Docker/CLI para a app em src.main:app.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        factory=False,
    )
