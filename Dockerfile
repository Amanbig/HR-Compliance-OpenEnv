FROM python:3.10-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml README.md ./
RUN uv sync --no-install-project

COPY . .

# Gradio default port
EXPOSE 7860

ENV PYTHONUNBUFFERED=1

CMD ["/app/.venv/bin/python", "app.py"]
