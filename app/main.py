from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.nba.loader import load_artifacts
from app.nba.router import router as nba_router
from app.nba.service import NBAService
from app.nba.settings import resolve_artifact_paths


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the frozen NBA artifacts once; fail startup if any is missing."""
    app.state.nba_service = NBAService(load_artifacts(resolve_artifact_paths()))
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(nba_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Report HTTP application liveness (not model readiness)."""
    return {"status": "ok"}
