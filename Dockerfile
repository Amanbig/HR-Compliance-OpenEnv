FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY . .

# Install all dependencies declared in pyproject.toml into the system Python
RUN uv pip install --no-cache --system .

EXPOSE 7860

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
