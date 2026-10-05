import pytest

from app.agent.service import AgentService, build_agent_service
from app.execution.adapters import SimulatedHandoffQueue, SimulatedOfferSender
from app.execution.service import ExecutionService
from app.nba.service import NBAService
from tests.nba.fakes import CHILE_PROBABILITIES, StubModel, build_artifacts


class SpyGraph:
    """Wraps a compiled graph and records invocations."""

    def __init__(self, graph):
        self.graph = graph
        self.invocations = []

    def invoke(self, state):
        self.invocations.append(state)
        return self.graph.invoke(state)


@pytest.fixture
def artifacts():
    return build_artifacts(StubModel(CHILE_PROBABILITIES))


@pytest.fixture
def nba_service(artifacts):
    return NBAService(artifacts)


@pytest.fixture
def execution_service(nba_service):
    return ExecutionService(nba_service, SimulatedOfferSender(), SimulatedHandoffQueue())


@pytest.fixture
def spy_graph(artifacts, nba_service):
    return SpyGraph(build_agent_service(artifacts, nba_service)._graph)


@pytest.fixture
def agent_service(spy_graph, nba_service):
    return AgentService(spy_graph, nba_service)
