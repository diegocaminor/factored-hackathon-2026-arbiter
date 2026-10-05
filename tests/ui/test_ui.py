import re

import pytest
from fastapi.testclient import TestClient

from app.main import STATIC_DIR, app

# No `with`: the lifespan (artifact loading) is not needed to serve static files.
client = TestClient(app)


def test_index_serves_html_with_local_assets():
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '/static/app.js' in response.text
    assert '/static/styles.css' in response.text


@pytest.mark.parametrize(
    ("path", "content_type"),
    [("/static/app.js", "javascript"), ("/static/styles.css", "text/css")],
)
def test_static_assets_are_served(path, content_type):
    response = client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


def test_index_is_not_in_openapi():
    assert "/" not in client.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize("name", ["index.html", "app.js", "styles.css"])
def test_no_external_urls(name):
    text = (STATIC_DIR / name).read_text(encoding="utf-8")

    assert "http://" not in text
    assert "https://" not in text


ALLOWED_API_PATHS = {
    "/customers/{id}/next-best-action",
    "/customers/{id}/confirm",
    "/customers/{id}/handoff",
    "/agent/run",
}


def api_paths_in_script():
    script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    literals = re.findall(r"[`'\"](/[^`'\"\s]*)[`'\"]", script)
    return {re.sub(r"\$\{[^}]*\}", "{id}", literal).split("?", 1)[0] for literal in literals}


def test_script_calls_only_existing_endpoints():
    paths = api_paths_in_script()

    # Every API path the UI calls is an existing endpoint, and all four are used.
    assert paths == ALLOWED_API_PATHS
