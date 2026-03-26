FROM python:3.10-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

# Gradio default port
EXPOSE 7860

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
