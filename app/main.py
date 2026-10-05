from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.router import router as agent_router
from app.agent.service import build_agent_service
from app.execution.adapters import SimulatedHandoffQueue, SimulatedOfferSender
from app.execution.router import router as execution_router
from app.execution.service import ExecutionService
from app.nba.loader import load_artifacts
from app.nba.router import router as nba_router
from app.nba.service import NBAService
from app.nba.settings import resolve_artifact_paths


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the frozen NBA artifacts once; fail startup if any is missing."""
    artifacts = load_artifacts(resolve_artifact_paths())
    nba_service = NBAService(artifacts)
    app.state.nba_service = nba_service
    app.state.execution_service = ExecutionService(
        nba_service, SimulatedOfferSender(), SimulatedHandoffQueue()
    )
    app.state.agent_service = build_agent_service(artifacts, nba_service)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(nba_router)
app.include_router(execution_router)
app.include_router(agent_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Report HTTP application liveness (not model readiness)."""
    return {"status": "ok"}
