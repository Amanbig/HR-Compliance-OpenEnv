FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml || \
    uv pip install --no-cache pydantic>=2.0 openai>=1.0 pyyaml "gradio>=4.0" python-dotenv Faker uvicorn fastapi

COPY . .

EXPOSE 7860

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "app.py"]
