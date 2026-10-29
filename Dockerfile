# MedVisionAI web app: React frontend + FastAPI backend in one container (Google Cloud Run or Hugging Face Spaces).

# ---- 1. build the React frontend
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ---- 2. Python API serving the models and the built frontend
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
WORKDIR /app
COPY server/requirements.txt server/requirements.txt
RUN pip install -r server/requirements.txt

USER user
ENV HOME=/home/user HF_HOME=/home/user/.cache/huggingface
COPY --chown=user medvision/ medvision/
COPY --chown=user server/ server/
COPY --chown=user models/ models/
COPY --chown=user examples/ examples/
COPY --chown=user braintumor/ braintumor/
COPY --chown=user assets/ assets/
COPY --from=web --chown=user /web/dist web/dist
# download the Phikon backbone now, so the first colorectal analysis does not wait for it
RUN python -c "from medvision.classifier import load_classifier; load_classifier()"

EXPOSE 7860
# Cloud Run sets PORT (8080); Hugging Face Spaces uses 7860
CMD ["sh", "-c", "exec uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-7860} --timeout-keep-alive 75"]
