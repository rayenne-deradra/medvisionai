"""Deploy the MedVisionAI web app (React + FastAPI) to a Hugging Face Space.

One-time setup (on your own computer):
    1. Create a free account at https://huggingface.co and an access token with "write" permission
       (Settings -> Access Tokens -> Create new token -> Write).
    2. .venv\\Scripts\\python.exe -c "from huggingface_hub import login; login()"     (paste the token when asked)

Deploy (and redeploy after every change):
    .venv\\Scripts\\python.exe tools\\deploy_hf.py --space YOUR-HF-USERNAME/medvisionai

It creates the Space (Docker) if needed, copies the secrets from .streamlit/secrets.toml into the Space's private
secrets (activation codes, AI keys, Supabase), and uploads the code and models. Hugging Face then builds the image
(about 10 minutes the first time) and serves the app at https://YOUR-HF-USERNAME-medvisionai.hf.space
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_KEYS = ["ACTIVATION_SECRET", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "GEMINI_API_KEY", "GEMINI_MODEL",
               "SUPABASE_URL", "SUPABASE_KEY", "HOSPITAL_NAME", "HOSPITAL_ADDRESS", "OPEN_ACCESS"]
UPLOAD = ["Dockerfile", ".dockerignore", "server/**", "medvision/**", "models/**", "examples/**", "braintumor/**",
          "assets/**", "web/package.json", "web/package-lock.json", "web/index.html", "web/tsconfig.json",
          "web/vite.config.ts", "web/public/**", "web/src/**"]
IGNORE = ["**/__pycache__/**", "**/*.pyc", "web/node_modules/**", "web/dist/**"]

SPACE_CARD = """---
title: MedVisionAI
emoji: 🩺
colorFrom: indigo
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Clinical Intelligence Platform for medical imaging
---

# MedVisionAI: Clinical Intelligence Platform for medical imaging

Brain tumour MRI (BRISC 2025 CNN ensemble, U-Net segmentation, triage score) and colorectal histopathology
(Phikon foundation model, Grad-CAM), with an AI assistant for medical questions and specialist referrals.

React frontend + FastAPI backend. API documentation: `/docs`.

**Research prototype, not a medical device. Not for diagnosis.**
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--space", required=True, help="YOUR-HF-USERNAME/space-name")
    ap.add_argument("--private", action="store_true", help="make the Space private (judges then need access)")
    ap.add_argument("--no-secrets", action="store_true", help="do not copy secrets from .streamlit/secrets.toml")
    a = ap.parse_args()

    from huggingface_hub import HfApi
    api = HfApi()
    try:
        user = api.whoami()["name"]
    except Exception:
        sys.exit("Not logged in to Hugging Face. Run:  .venv\\Scripts\\python.exe -c \"from huggingface_hub import login; login()\"")
    print(f"Logged in as {user}. Creating or updating the Space {a.space} ...")
    api.create_repo(a.space, repo_type="space", space_sdk="docker", private=a.private, exist_ok=True)

    if not a.no_secrets:
        path = ROOT / ".streamlit" / "secrets.toml"
        data = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        for key in SECRET_KEYS:
            if data.get(key):
                api.add_space_secret(a.space, key, str(data[key]))
                print(f"  secret {key}: set")
        if data.get("activation_codes"):    # only hashes of the codes, never the codes themselves
            api.add_space_secret(a.space, "ACTIVATION_CODES", json.dumps(data["activation_codes"], default=str))
            print(f"  secret ACTIVATION_CODES: {len(data['activation_codes'])} licence(s)")

    print("Uploading code and models (the first upload sends ~250 MB) ...")
    api.upload_folder(repo_id=a.space, repo_type="space", folder_path=str(ROOT), allow_patterns=UPLOAD,
                      ignore_patterns=IGNORE, commit_message="Deploy MedVisionAI web app")
    api.upload_file(path_or_fileobj=SPACE_CARD.encode(), path_in_repo="README.md", repo_id=a.space, repo_type="space",
                    commit_message="Space card")
    owner, name = a.space.split("/")
    print(f"\nDone. Build progress: https://huggingface.co/spaces/{a.space}")
    print(f"Your app (after the build): https://{owner.lower()}-{name.lower().replace('_', '-')}.hf.space")


if __name__ == "__main__":
    main()
