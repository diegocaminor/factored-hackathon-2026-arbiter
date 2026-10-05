FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src/propensity/ ./src/propensity/
COPY app/ ./app/

ENV PYTHONPATH=/app/src \
    ARTIFACTS_DIR=/app/artifacts/propensity

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
