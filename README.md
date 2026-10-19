# MedVisionAI: Colorectal Tissue Analysis

**Early detection saves lives.** MedVisionAI is a Streamlit research app for **colorectal histopathology**. Upload an
H&E image of colon or rectum tissue to get a **9-class tissue classification with calibrated confidence scores**, a
**tumour finding**, a **classification report** and a **Grad-CAM overlay**. A separate **AI Assistant** page (OpenAI)
lets you discuss analysed or attached images, or ask general questions, like ChatGPT. It uses OpenAI first and
falls back to **Google Gemini** (free tier) when OpenAI fails, for example when the account has no credits.

> ⚠️ **Research prototype, not a medical device.** Not clinically validated or approved by any regulator. Results are
> not a diagnosis and must not be used for clinical decisions. Do not upload images that identify a patient.

---

## For judges: evaluate in 5 minutes

**Live app:** LIVE_APP_URL  (no installation needed)

1. **Tissue analysis → "Try an example".** Click *Colorectal adenocarcinoma epithelium*: expect **Tumour tissue
   detected**, high confidence, calibrated scores for all 9 tissue types, and a Grad-CAM overlay next to the original.
2. Click *Normal colon mucosa* or *Adipose*: expect **No tumour tissue detected**.
3. Click *Mosaic 16 patches*: the image is scanned as 16 tiles; the 4 tumour patches on the diagonal are flagged and
   highlighted.
4. Upload any grayscale picture (e.g. an X-ray): expect **Not assessed** with the reason. The model refuses to guess
   outside its domain.
5. Click **Discuss in AI Assistant**: the assistant explains the result with its uncertainty. Ask a follow-up, switch
   pages and come back; the chat is kept.
6. **Model card** (sidebar) and the [results table](#results-same-900-crc-val-he-7k-images-100-per-class-50-patients-never-seen-in-training)
   below: how the model was chosen and validated on 50 patients never seen in training.

To run it locally instead, see [Setup](#setup-local). To reproduce the tests: `pip install -r requirements-eval.txt`
then `pytest -q`.

---

## Pages

| Page | What it does |
|---|---|
| **Tissue analysis** | Upload (or pick a CRC-VAL-HE-7K example) → finding (*Tumour tissue detected* / *No tumour tissue detected* / *Not assessed*), predicted tissue type, calibrated probabilities for all 9 classes, confidence level with reasons, original image next to a semi-transparent Grad-CAM overlay, JSON report and overlay downloads. Large images are scanned tile by tile. Earlier analyses stay available in the sidebar. |
| **AI Assistant** | ChatGPT-style chat. Attach an analysis (image + overlay + report) or your own pictures, or just ask. Multiple chats; history is kept while you switch pages. Export as Markdown. |

The 9 classes (NCT-CRC-HE-100K): adipose tissue, background, debris/necrosis, lymphocytes, mucus, smooth muscle,
normal colon mucosa, cancer-associated stroma, **colorectal adenocarcinoma epithelium (tumour)**.

---

## The model, and why it was chosen

### The problem with the previous model
The previous colorectal model (ConvNeXt-Tiny v3) looked good on clean test images but **downscaled every image to
64 px** and was trained on a narrow colour range. Under a simulated stain/lab colour shift, its tumour recall
collapsed (see table). That is the unreliability users saw on real-world images.

### Options evaluated

| Option | Verdict |
|---|---|
| **General multimodal API (OpenAI GPT)** used as the classifier | **Rejected as classifier.** Not trained or validated for tissue classification; no calibrated probabilities; outputs can change between model versions. Used only to *explain* results and chat. `evaluation/evaluate_openai.py` measures its zero-shot accuracy on the same test images. A run on 2026-10-19 could not score any image: the OpenAI account had no credits left (`insufficient_quota`). Re-run it after adding credits (~180 small requests). |
| Previous ConvNeXt-Tiny v3 (28M, 64 px) | Baseline. Fragile under colour shift. |
| **Phikon** (Owkin, ViT-B/16, 86M) + linear head | **Selected.** Self-supervised on 43M H&E tiles from 16 TCGA cancer types *including colon and rectum*, public weights, 224 px input. |
| Lunit DINO ViT-S/8 (22M) + linear head | Evaluated (table below). Best under strong colour shift, but tumour recall drops to ~62% on compressed/web-like images; slower on CPU. |
| UNI / UNI2, Virchow2, CONCH, H-optimus-0, Prov-GigaPath | Not used: gated downloads and/or 300M–1.1B parameters, too large for a free CPU deployment. |

Approach: **transfer learning with a frozen foundation model**. Only a small linear layer (9 × 768 weights) is trained on
NCT-CRC-HE-100K. Its temperature is calibrated on validation data. The backbone is downloaded unchanged from Hugging Face.
Nothing large is trained from scratch.

### Results: same 900 CRC-VAL-HE-7K images (100 per class, 50 patients never seen in training)

Each cell: 9-class accuracy · tumour recall · tumour precision.

| Condition | Previous ConvNeXt v3 | **Phikon + head (selected)** | Lunit ViT-S/8 + head |
|---|---|---|---|
| Original images | 93.6% · 98% · 91.6% | **95.1% · 100% · 97.1%** | 94.6% · 97% · 100% |
| Mild stain shift | 82.6% · 80% · 90.9% | 88.4% · **99%** · 96.1% | **91.9%** · 97% · 100% |
| Strong stain shift | 53.1% · 39% · 83.0% | 67.7% · 68% · 98.6% | **72.8% · 73%** · 98.6% |
| JPEG quality 40 | 92.6% · 96% · 91.4% | **94.3% · 99%** · 100% | 86.0% · 63% · 100% |
| Blur | 93.8% · 97% · 94.2% | **94.7% · 99%** · 94.3% | 94.1% · 99% · 99.0% |
| Web-like (mild shift + downscale + JPEG 60) | 82.4% · 81% · 91.0% | **86.8% · 95%** · 99.0% | 84.7% · 62% · 100% |

**Why Phikon:** it has the best (or tied) tumour recall in 5 of 6 conditions. Lunit handles strong colour shifts slightly
better, but it misses over a third of tumour patches in compressed and web-like images, which is what most uploads
look like (JPEG screenshots and photos). Phikon is also faster on CPU here (~2.3 vs ~1.5 img/s).

**Reading this honestly:** under a *strong* stain shift every model degrades (Phikon catches 68% of tumour patches).
Images from very different labs or scanners remain a real limitation, and the app says so. The test uses 900 patches;
a 95% interval on 95% accuracy is roughly ±1.5 points. The Lunit head is kept in `models/` and can be selected with
`MEDVISION_BACKEND = "lunit_vits8"`.

Accuracy is 9-class accuracy. Recall and precision are for the tumour class. Stain shifts use the same scikit-image
HED perturbation, seeds and images as the original `robustness.py`. Full numbers, including macro-F1 and AUROC, are in
`reports/model_comparison.json` and `reports/benchmark_phikon.json`.

---

## Project structure

```
medvisionai_chat/
├── app.py                        entry point: theme, logo, navigation (Tissue analysis, AI Assistant)
├── views/
│   ├── analysis.py               upload → classification report, confidence scores, Grad-CAM overlay
│   └── assistant.py              ChatGPT-style chat with image attachments and analysis hand-off
├── medvision/
│   ├── config.py                 paths, limits, secret lookup (st.secrets first, environment fallback)
│   ├── imaging.py                image validation, H&E applicability check, tiling, semi-transparent overlay
│   ├── analysis.py               runs the classifier (single patch / tile scan), builds the report
│   ├── chat.py                   chat storage and history → OpenAI messages
│   ├── classifier/
│   │   ├── base.py               TissueClassifier interface  ◄── implement this for another model
│   │   ├── foundation.py         Phikon / Lunit backbone + linear head + ViT Grad-CAM
│   │   └── registry.py           loads models/crc_head_<backbone>.pt
│   ├── llm/providers.py          OpenAI client (streaming, retries, key never leaked)
│   ├── llm/prompts.py            assistant system prompt
│   └── ui/                       theme, report card, shared session state
├── models/crc_head_phikon.pt     trained linear head (~30 KB); the backbone is downloaded on first run
├── evaluation/benchmark.py       reproducible benchmark + head training
├── evaluation/evaluate_openai.py zero-shot test of a general multimodal model
├── reports/                      benchmark results (JSON)
├── examples/                     10 CRC-VAL-HE-7K test patches + a 16-patch mosaic (tumour on the diagonal)
├── tests/                        pytest: image handling, chat, OpenAI client, real-model tests
├── .streamlit/config.toml, .streamlit/secrets.toml.example
└── requirements.txt, requirements-eval.txt, .gitignore
```

---

## Quick start on Windows

Double-click **`run_app.bat`** in the `medvisionai_chat` folder. The first time, it creates `.venv` and installs the
packages. Then it opens the app at <http://localhost:8501>. Or, in PowerShell:

```powershell
cd C:\Users\anera\OneDrive\Desktop\medvision_package\medvisionai_chat
.\.venv\Scripts\python.exe -m streamlit run app.py
```

(`streamlit run app.py` alone only works when the virtual environment is activated and you are inside this folder.)

## Setup (local)

Python 3.10–3.14. About 2 GB of disk for PyTorch and the model. No GPU is needed.

```bash
cd medvisionai_chat
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### AI keys (only for the AI Assistant)

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml       # Windows: copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-..."     # tried first (paid API credits; ChatGPT Plus does not include API usage)
GEMINI_API_KEY = "..."        # free fallback: create at https://aistudio.google.com/apikey
```

Either key alone is enough. OpenAI is tried first. If it fails before answering (no credits, rate limit, outage),
Gemini answers instead, and the reply caption says which model answered and why. After OpenAI reports "no credits",
it is skipped for the rest of the browser session; refresh the page after adding credits.

The app reads the keys as `st.secrets["OPENAI_API_KEY"]` and `st.secrets["GEMINI_API_KEY"]`. The file is listed in `.gitignore`, and keys are never printed,
logged or shown in the UI. Error messages are scrubbed of it. If the key is missing, Tissue analysis still works and
the AI Assistant shows setup instructions instead of failing. Use **Test connection** on the AI Assistant page to check
the key. The model is picked automatically, or you can set `OPENAI_MODEL`.

### Run

```bash
streamlit run app.py
```

The first analysis downloads the Phikon backbone from Hugging Face (~350 MB, cached afterwards).

---

## Testing the updated app

1. `pip install -r requirements-eval.txt`, then `pytest -q`. This runs image/tiling/chat/OpenAI-client tests and
   real-model tests on the bundled examples.
2. `streamlit run app.py` → **Tissue analysis**:
   - open *Try an example* and click **Colorectal adenocarcinoma epithelium**: expect *Tumour tissue detected*, high
     confidence, and the overlay tinting the epithelium;
   - click **Normal colon mucosa** and **Adipose**: expect *No tumour tissue detected*;
   - click the **Mosaic** example: expect a tile scan of 16 tiles, with tumour tiles on the diagonal highlighted;
   - upload a chest X-ray or any grayscale image: expect *Not assessed* with an explanation;
   - move **Heatmap opacity** in the sidebar: the overlay changes, and untinted tissue keeps its original colours.
3. **Discuss in AI Assistant**: the assistant opens with the analysis attached and explains it. Ask a follow-up, switch
   back to Tissue analysis and return: the chat is still there.
4. On the AI Assistant page, ask a general question (no attachment) and attach a picture with **+**.
5. Without `secrets.toml`, the assistant shows the offline notice, and analysis keeps working.

---

## Deploy on Streamlit Community Cloud

1. Push this folder to GitHub (`git status` must **not** list `.streamlit/secrets.toml`).
2. On <https://share.streamlit.io>: **Create app**, then pick the repository, branch, and main file `app.py`.
3. **Advanced settings**: choose Python 3.12, then paste into **Secrets**:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. Deploy. The first start downloads the backbone. Phikon in float32 needs ~350 MB of RAM in addition to PyTorch.

---

## Retraining / re-benchmarking the head

```bash
pip install -r requirements-eval.txt
python evaluation/benchmark.py --train "data/nct_train_*.parquet" --test data/CRC-VAL-HE-7K \
       --train-per-class 100 --test-per-class 100 --backbones phikon
```

`--train` takes parquet files from <https://huggingface.co/datasets/1aurent/NCT-CRC-HE> (NCT-CRC-HE-100K, CC BY 4.0).
CRC-VAL-HE-7K is on Zenodo (record 1214456). The script caches features, so reruns are fast.

## Integrating another model

Implement `TissueClassifier.explain(images, class_index)` → `(probabilities (N, 9), heatmaps (N, h, w))` in a new file under
`medvision/classifier/`, register a loader in `registry.py`, and select it with the secret `MEDVISION_BACKEND`.

## Licences

Phikon weights: Owkin non-commercial licence (research use). NCT-CRC-HE-100K / CRC-VAL-HE-7K: CC BY 4.0 (Kather et al.,
2019). Grad-CAM: Selvaraju et al., 2017.
