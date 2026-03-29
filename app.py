"""
app.py — HF Space entry point.

Mounts the Gradio UI (src/ui.py) onto the FastAPI app (server/app.py)
and starts the uvicorn server.
"""

import gradio as gr

from server.app import app  # FastAPI with /reset /step /state /health
from src.config import CSS  # Shared stylesheet
from src.ui import demo  # Gradio Blocks UI

# Mount Gradio onto FastAPI — both run on the same port (7860)
app = gr.mount_gradio_app(
    app,
    demo,
    path="/",
    css=CSS,
    theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
