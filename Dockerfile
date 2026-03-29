FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy only dependency file first for layer caching
COPY pyproject.toml .

# Install dependencies only (not the project itself)
RUN uv pip install --no-cache --system pydantic openai pyyaml python-dotenv Faker uvicorn fastapi openenv-core

# Copy the rest of the code
COPY . .

EXPOSE 7860

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
