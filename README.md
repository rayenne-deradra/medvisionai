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

**Live app:** [https://medvisionai-umzyc5lnqey9cnldfitteg.streamlit.app/](https://medvisionai-umzyc5lnqey9cnldfitteg.streamlit.app/) (no installation needed)

0. **Sign in** with the evaluation activation code provided with our submission (format `MVAI-XXXX-XXXX-XXXX-XXXX`).
   MedVisionAI is licensed per organisation; see [Licensing](#licensing-activation-codes).
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

## Licensing (activation codes)

MedVisionAI is offered to hospitals, laboratories and research groups as a subscription. After an organisation's
payment is confirmed, it receives an **activation code** (`MVAI-XXXX-XXXX-XXXX-XXXX`) that unlocks the app for that
organisation until its expiry date. The sidebar shows who the app is licensed to; **Sign out** clears the session's
analyses and chats.

How it is secured:

- Codes are **never stored in plain text**. Streamlit secrets hold only an HMAC-SHA256 of each code (keyed with a
  private `ACTIVATION_SECRET`), so neither the source code nor the secrets list reveals a usable code.
- Each licence has an organisation, a plan, an optional **expiry date** and an `active` flag for **instant revocation**.
- **Brute-force protection:** after 5 wrong codes, sign-in is paused for 60 seconds.
- Every page is protected: opening any address while signed out leads to the sign-in page.
- **Remember this device** (on by default): after a successful code, the browser keeps a signed cookie for 30 days
  (never past the licence's expiry), so a refresh does not ask for the code again. The cookie holds no activation
  code, cannot be forged without `ACTIVATION_SECRET`, and is re-checked on every visit, so revoking or expiring a
  licence also signs out remembered devices. **Sign out** deletes it.

Issuing a code after payment (on your own computer):

```bash
python tools/make_activation_code.py --org "Acme Hospital, Pathology" --expires 2027-10-31 --plan Research
```

The script prints the code (send it to the customer; it is shown only once) and the lines to paste into Streamlit
secrets. To revoke a licence, set `active = false` in its entry, or delete the entry. If no licences are configured,
the app runs in open demo mode (useful for local development).

## Pages

| Page | What it does |
|---|---|
| **Tissue analysis** | Upload (or pick a CRC-VAL-HE-7K example) → finding (*Tumour tissue detected* / *No tumour tissue detected* / *Not assessed*), predicted tissue type, calibrated probabilities for all 9 classes, confidence level with reasons, original image next to a semi-transparent Grad-CAM overlay, JSON report and overlay downloads. Large images are scanned tile by tile. Earlier analyses stay available in the sidebar. |
| **AI Assistant** | Attach an analysis (image + overlay + report) or your own pictures, or just ask. Multiple chats; history is kept while you switch pages. Export as Markdown. |

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
| **General multimodal API (OpenAI GPT)** used as the classifier | **Rejected as classifier.** Not trained or validated for tissue classification; no calibrated probabilities; outputs can change between model versions. Used only to *explain* results and chat. `evaluation/evaluate_openai.py` measures its zero-shot accuracy on the same test images (~180 small API requests). |
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
cd path\to\medvisionai
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


### Run

```bash
streamlit run app.py
```

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

## Retraining / re-benchmarking the head

```bash
pip install -r requirements-eval.txt
python evaluation/benchmark.py --train "data/nct_train_*.parquet" --test data/CRC-VAL-HE-7K \
       --train-per-class 100 --test-per-class 100 --backbones phikon
```

`--train` takes parquet files from <https://huggingface.co/datasets/1aurent/NCT-CRC-HE> (NCT-CRC-HE-100K, CC BY 4.0).
CRC-VAL-HE-7K is on Zenodo (record 1214456). The script caches features, so reruns are fast.


## Limitations

**Project constraints**
- **Time:** MedVisionAI was built in about **4 weeks**. That is enough for a working, tested research prototype, but
  not for what a medical AI system normally requires: multi-centre data collection, clinical validation, pathologist
  review of results, regulatory documentation and long-term testing.
- **Team:** the project was developed by a single person. A full medical AI project typically involves pathologists
  to label and review cases, machine-learning engineers, software engineers, and clinical, ethical and regulatory
  advisers. Without them, there was no expert annotation, no clinical feedback loop and no independent review.
- **Hardware:** all training and evaluation ran on a laptop CPU (4 cores, no GPU). This is why:
  - only a frozen foundation model with a small linear head was trained, instead of fine-tuning the whole network;
  - the head was trained on 1,800 images instead of the full 100,000-image dataset;
  - the benchmark used 900 test patches instead of the full 7,180-image test set;
  - larger and potentially stronger pathology models (e.g. UNI2, Virchow2, H-optimus) could not be evaluated.
- With more time, a multidisciplinary team and GPU resources, most of the limitations listed below could be
  addressed (see *Future work*).

**Medical use**
- MedVisionAI is a research prototype, not a medical device. It has not been clinically validated or approved by any
  regulator, and its output must never be used for diagnosis or treatment decisions.
- It was validated on image **patches**, not on whole slides, real clinical workflows or pathologist comparisons.

**Data and scope**
- The classifier covers **colorectal tissue only** (9 tissue types). Other organs, other tumour types, polyps and
  adenomas, tumour grading, staging and molecular subtypes are outside its training.
- Training data (NCT-CRC-HE-100K) comes from one German centre (NCT Heidelberg). The external test set
  (CRC-VAL-HE-7K, 50 patients) is from the same institution, so it does not prove performance at other hospitals.
- Only 1,800 training images (100 per class per stain version) were used for the classification head. The
  benchmark used 900 test patches, so reported accuracies have a margin of roughly ±1.5 percentage points.

**Robustness**
- Performance drops when staining looks very different from the training data. Under a strong simulated stain shift,
  accuracy falls to 67.7% and tumour recall to 68%. Images from other labs or scanners may be less reliable.
- The model expects patches of about 224 × 224 px at ~20× magnification. Screenshots or whole-slide overviews at
  unknown magnification are scanned tile by tile; this tile scan and its "tumour tiles needed" rule are heuristics
  that were not validated at slide level.
- *Cancer-associated stroma* and *debris* are the classes most often confused.
- The image check that rejects non-H&E images (e.g. X-rays) is a simple colour heuristic and can be fooled.

**Explanations**
- Grad-CAM shows which regions influenced the model, not proof of disease. The heatmap has low resolution
  (14 × 14 grid per patch), so it highlights areas, not individual cells.
- Probabilities are calibrated on validation data but can still be over-confident on unusual images.

**AI Assistant**
- Answers come from general-purpose language models (OpenAI, Google Gemini). They are not validated for pathology,
  can be wrong or inconsistent, and may change when providers update their models.
- Images and questions sent to the assistant are processed by the provider's servers; do not upload images that
  identify a patient.
- The assistant depends on API availability and quotas: answers can be slow or fail when a provider is overloaded
  or a free-tier limit is reached.

**Software**
- Runs on CPU: the first analysis downloads the backbone (~350 MB), and a large tile scan can take tens of seconds.
- Analyses and chats are kept only for the browser session and are lost on refresh; there are no user accounts,
  audit log or persistent storage.

## Future work

**Validation**
- Test on external cohorts from other hospitals, scanners and countries (e.g. TCGA-COAD/READ, PAIP), and report
  per-site results.
- Validate at whole-slide level, and run a reader study comparing the tool with pathologists, with and without AI
  assistance.
- Measure the zero-shot accuracy of general multimodal models (`evaluation/evaluate_openai.py`) to document why
  they are not used as classifiers.

**More medical imaging types**
- Extend MedVisionAI beyond histopathology to **radiology**, starting with **CT and MRI** for colorectal cancer:
  - CT of the chest, abdomen and pelvis for staging and for finding liver and lung metastases;
  - pelvic MRI for local staging of rectal cancer and assessing response to treatment;
  - later, other modalities such as PET-CT, ultrasound and colonoscopy images or video.
- Support the DICOM format (multi-slice 3D volumes, window/level, patient-data removal) instead of only 2D PNG/JPEG.
- Use a separate, modality-specific model for each imaging type: pretrained radiology foundation models or 3D
  segmentation networks (e.g. MONAI-based models) fine-tuned on public datasets such as the Medical Segmentation
  Decathlon, TCIA collections and challenge datasets. The current histopathology model must not be reused for scans.
- Detect the image modality automatically and route each upload to the right model. Today the app recognises
  grayscale scans and answers "Not assessed" instead of guessing.
- Validate each new modality separately on external data, with the same robustness tests, uncertainty reporting and
  "research use only" safeguards as the tissue classifier.
- Long term, combine pathology, radiology and clinical information into one multimodal case summary that a clinician
  can review.

**Model**
- Train the head on the full 100,000-image dataset, with stronger stain augmentation and stain normalisation, to
  close the gap under strong colour shifts.
- Compare larger pathology foundation models (UNI2, Virchow2, H-optimus) on a GPU deployment, and try ensembles or
  light fine-tuning of the last backbone layers.
- Add uncertainty estimation and out-of-distribution detection, so the app can say "this image is unlike anything
  I was trained on" more reliably than the current colour check.
- Extend beyond tissue type: tumour grading, MSI/MMR status prediction, and polyp classification.

**Whole-slide support**
- Read whole-slide image formats (SVS, NDPI) with OpenSlide, detect tissue automatically, and show a slide-level
  tumour map instead of fixed tiles.
- Ask the user for (or read) the magnification so tiles match the training scale.

**Explanations and assistant**
- Add higher-resolution and more faithful explanation methods (e.g. attention maps, integrated gradients), with a
  quantitative faithfulness test.
- Ground the assistant's answers in cited sources (retrieval from pathology guidelines and papers), and evaluate
  its answers with pathologists.
- Offer a fully local, open-source vision-language model option, so no image leaves the computer.

**Engineering**
- GPU inference for faster tile scans, optional user accounts with saved case history, and PDF report export.
- Continuous integration that runs the tests and the benchmark on every change.

## Licences

Phikon weights: Owkin non-commercial licence (research use). NCT-CRC-HE-100K / CRC-VAL-HE-7K: CC BY 4.0 (Kather et al.,
2019). Grad-CAM: Selvaraju et al., 2017.
