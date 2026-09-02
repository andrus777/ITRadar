from fastapi import FastAPI

from app.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return the basic application liveness status."""
    return {"status": "ok"}

