import pytest

from app.execution.service import ExecutionService
from app.nba.service import NBAService
from tests.execution.fakes import SpyHandoffQueue, SpyOfferSender
from tests.nba.fakes import CHILE_PROBABILITIES, StubModel, build_artifacts


@pytest.fixture
def nba_service():
    return NBAService(build_artifacts(StubModel(CHILE_PROBABILITIES)))


@pytest.fixture
def offer_sender():
    return SpyOfferSender()


@pytest.fixture
def handoff_queue():
    return SpyHandoffQueue()


@pytest.fixture
def execution_service(nba_service, offer_sender, handoff_queue):
    return ExecutionService(nba_service, offer_sender, handoff_queue)
