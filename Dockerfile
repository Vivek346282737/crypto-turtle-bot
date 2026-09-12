FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .

COPY src/ ./src/
COPY configs/ ./configs/

ENV PYTHONUNBUFFERED=1
ENV TRADING_MODE=paper

CMD ["python", "src/trading_bot/core/engine.py"]
