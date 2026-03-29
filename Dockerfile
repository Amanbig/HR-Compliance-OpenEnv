FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY . .

# Install all dependencies declared in pyproject.toml
RUN uv venv /app/.venv && \
    /app/.venv/bin/uv pip install --no-cache .

EXPOSE 7860

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "app.py"]
