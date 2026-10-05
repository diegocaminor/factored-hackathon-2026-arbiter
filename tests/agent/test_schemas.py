import pytest
from pydantic import ValidationError

from app.agent.schemas import AgentRunRequest, AgentRunResponse


def test_request_accepts_json_booleans():
    assert AgentRunRequest.model_validate({"customer_id": "CLI-X", "user_confirmed": False})


@pytest.mark.parametrize(
    "payload",
    [
        {"customer_id": "CLI-X"},
        {"user_confirmed": True},
        {"customer_id": "CLI-X", "user_confirmed": "true"},
        {"customer_id": "CLI-X", "user_confirmed": 1},
        {"customer_id": "CLI-X", "user_confirmed": None},
    ],
)
def test_request_rejects_missing_or_non_boolean(payload):
    with pytest.raises(ValidationError):
        AgentRunRequest.model_validate(payload)


def test_response_schema_renders():
    schema = AgentRunResponse.model_json_schema()

    assert {"customer_id", "status", "recommendation", "execution_result"} <= set(
        schema["properties"]
    )
    assert "customer_row" not in schema["properties"]
    assert "ranked_actions" not in schema["properties"]
