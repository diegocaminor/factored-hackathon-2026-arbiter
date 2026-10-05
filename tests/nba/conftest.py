import pytest

from app.nba.service import NBAService
from tests.nba.fakes import CHILE_PROBABILITIES, StubModel, build_artifacts


@pytest.fixture
def stub_model():
    return StubModel(CHILE_PROBABILITIES)


@pytest.fixture
def nba_service(stub_model):
    return NBAService(build_artifacts(stub_model))
