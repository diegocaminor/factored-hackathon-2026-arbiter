from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    """Report HTTP application liveness (not model readiness)."""
    return {"status": "ok"}
