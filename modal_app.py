"""MedVisionAI web app (React + FastAPI) on Modal: free monthly credits, no card, wakes up by itself on the first visit.

Deploy with:  .venv\\Scripts\\python.exe tools\\deploy_modal.py      (see that file for the one-time login)
Live at:      https://<your-modal-workspace>--medvisionai.modal.run
"""
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
NO_CACHE = ["**/__pycache__/**", "**/*.pyc"]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libglib2.0-0")
    .pip_install_from_requirements(str(ROOT / "server" / "requirements.txt"))
    .env({"PYTHONUNBUFFERED": "1", "OMP_NUM_THREADS": "2", "HF_HOME": "/root/.cache/huggingface"})
    .workdir("/app")
    .add_local_dir(ROOT / "medvision", "/app/medvision", copy=True, ignore=NO_CACHE)
    .add_local_dir(ROOT / "models", "/app/models", copy=True)
    .add_local_dir(ROOT / "assets", "/app/assets", copy=True)
    # bake the Phikon pathology backbone into the image, so no visitor waits for the download
    .run_commands('python -c "from medvision.classifier import load_classifier; load_classifier()"')
    .add_local_dir(ROOT / "braintumor", "/app/braintumor", ignore=NO_CACHE)
    .add_local_dir(ROOT / "examples", "/app/examples")
    .add_local_dir(ROOT / "server", "/app/server", ignore=NO_CACHE)
    .add_local_dir(ROOT / "web" / "dist", "/app/web/dist")
)

app = modal.App("medvisionai")


@app.function(image=image, secrets=[modal.Secret.from_name("medvisionai-secrets")], cpu=2.0, memory=4096,
              timeout=600, scaledown_window=1200,   # stays warm 20 minutes after the last visit
              max_containers=1)                      # one instance: analysed cases stay available to the assistant
@modal.concurrent(max_inputs=16)
@modal.asgi_app(label="medvisionai")
def web():
    import sys
    import threading

    sys.path.insert(0, "/app")
    from server.main import app as api, brain_engine, tissue_classifier

    def warm_up():           # load both models in the background while the first page is shown
        for load in (brain_engine, tissue_classifier):
            try:
                load()
            except Exception as e:        # a model error is reported by the endpoint that needs it
                print(f"warm-up: {e}")

    threading.Thread(target=warm_up, daemon=True).start()
    return api
