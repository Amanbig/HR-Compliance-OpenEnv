"""
app.py — HF Space entry point.

Mounts the Gradio UI (src/ui.py) onto the FastAPI app (server/app.py)
and starts the uvicorn server.
"""

import gradio as gr

from server.app import app  # FastAPI with /reset /step /state /health
from src.ui import demo  # Gradio Blocks UI

# Pre-initialise Gradio's event queue so first request is fast
demo.queue()

# Mount Gradio onto FastAPI — both run on the same port (7860)
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
