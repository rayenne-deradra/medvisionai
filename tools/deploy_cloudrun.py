"""Deploy the MedVisionAI web app to Google Cloud Run: scales to zero, so it costs nothing while nobody uses it.

One-time setup (on your own computer):
    1. Create a Google Cloud project with billing enabled (https://console.cloud.google.com).
    2. Install the Google Cloud CLI:      winget install Google.CloudSDK
    3. In a NEW terminal:                 gcloud auth login
                                          gcloud config set project YOUR-PROJECT-ID

Deploy (and redeploy after every change), in the medvisionai_chat folder:
    .venv\\Scripts\\python.exe tools\\deploy_cloudrun.py

Google Cloud Build builds the Dockerfile (frontend + API + models) and Cloud Run serves it. The secrets from
.streamlit/secrets.toml (only hashes of activation codes) become environment variables of the service; they are
written to a temporary file outside the project and deleted right after. The first build takes about 15 minutes.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_KEYS = ["ACTIVATION_SECRET", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "GEMINI_API_KEY", "GEMINI_MODEL",
               "SUPABASE_URL", "SUPABASE_KEY", "HOSPITAL_NAME", "HOSPITAL_ADDRESS", "OPEN_ACCESS"]
APIS = ["run.googleapis.com", "cloudbuild.googleapis.com", "artifactregistry.googleapis.com"]


def gcloud() -> str:
    exe = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not exe:
        sys.exit("The Google Cloud CLI is not installed. Run:  winget install Google.CloudSDK  then open a new terminal.")
    return exe


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--service", default="medvisionai")
    ap.add_argument("--region", default="europe-west1", help="a tier-1 region, covered by the Cloud Run free tier")
    a = ap.parse_args()
    g = gcloud()

    project = subprocess.run([g, "config", "get-value", "project"], capture_output=True, text=True).stdout.strip()
    if not project or project == "(unset)":
        sys.exit("No Google Cloud project selected. Run:  gcloud config set project YOUR-PROJECT-ID")
    print(f"Project: {project}  ·  region: {a.region}")
    subprocess.run([g, "services", "enable", *APIS], check=True)

    path = ROOT / ".streamlit" / "secrets.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    env = {k: str(data[k]) for k in SECRET_KEYS if data.get(k)}
    if data.get("activation_codes"):
        env["ACTIVATION_CODES"] = json.dumps(data["activation_codes"], default=str)

    fd, env_file = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for k, v in env.items():
                f.write(f"{k}: {json.dumps(v)}\n")     # JSON strings are valid YAML strings
        print(f"Secrets passed: {', '.join(sorted(env))}")
        print("Building and deploying (first time about 15 minutes) ...")
        subprocess.run([g, "run", "deploy", a.service, "--source", str(ROOT), "--region", a.region,
                        "--allow-unauthenticated", "--cpu", "2", "--memory", "4Gi", "--cpu-boost",
                        "--min-instances", "0", "--max-instances", "2", "--concurrency", "8", "--timeout", "600",
                        "--env-vars-file", env_file, "--quiet"], cwd=ROOT, check=True)
    finally:
        os.remove(env_file)


if __name__ == "__main__":
    main()
