"""Deploy the MedVisionAI web app to Modal (https://modal.com): free monthly credits, no card, no manual start.

One-time setup (on your own computer, in the medvisionai_chat folder):
    .venv\\Scripts\\python.exe -m modal setup        (opens the browser: sign up with GitHub or Google and approve)

Deploy (and redeploy after every change):
    .venv\\Scripts\\python.exe tools\\deploy_modal.py

It stores the secrets from .streamlit/secrets.toml in a private Modal secret ("medvisionai-secrets"; only hashes of
activation codes), then builds and deploys modal_app.py. The first build takes about 10 minutes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_NAME = "medvisionai-secrets"
SECRET_KEYS = ["ACTIVATION_SECRET", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "GEMINI_API_KEY", "GEMINI_MODEL",
               "SUPABASE_URL", "SUPABASE_KEY", "HOSPITAL_NAME", "HOSPITAL_ADDRESS", "OPEN_ACCESS"]


def main() -> None:
    import modal

    if not (ROOT / "web" / "dist" / "index.html").is_file():
        sys.exit("The frontend is not built. Run:  cd web && npm install && npm run build")
    path = ROOT / ".streamlit" / "secrets.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    env = {k: str(data[k]) for k in SECRET_KEYS if data.get(k)}
    if data.get("activation_codes"):
        env["ACTIVATION_CODES"] = json.dumps(data["activation_codes"], default=str)
    try:
        modal.Secret.objects.delete(SECRET_NAME)
    except Exception:
        pass                                   # first deploy: nothing to replace
    try:
        modal.Secret.objects.create(SECRET_NAME, env)
    except Exception as e:
        sys.exit(f"Could not save the secrets on Modal ({type(e).__name__}). Did you run "
                 "'.venv\\Scripts\\python.exe -m modal setup'?")
    print(f"Secrets stored: {', '.join(sorted(env))}")
    print("Building and deploying (first time about 10 minutes) ...")
    subprocess.run([sys.executable, "-m", "modal", "deploy", str(ROOT / "modal_app.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
