# MedVisionAI: Clinical Intelligence Platform

**Early detection saves lives.** MedVisionAI is a Streamlit research app for **colorectal histopathology**. Upload an
H&E image of colon or rectum tissue to get a **9-class tissue classification with calibrated confidence scores**, a
**tumour finding**, a **classification report** and a **Grad-CAM overlay**. A separate **AI Assistant** page lets you
discuss your analyses or attached medical images in a ChatGPT-style chat; it answers **medical and health questions
only**. It uses OpenAI first and falls back to **Google Gemini** (free tier) when OpenAI is unavailable.

> ⚠️ **Research prototype, not a medical device.** Not clinically validated or approved by any regulator. Results are
> not a diagnosis and must not be used for clinical decisions. Do not upload images that identify a patient.

---

## For judges: evaluate in 5 minutes

**Live app:** [https://medvisionai-umzyc5lnqey9cnldfitteg.streamlit.app/](https://medvisionai-umzyc5lnqey9cnldfitteg.streamlit.app/) (no installation needed)

> If the page says the app has gone to sleep, click the button to wake it and wait about a minute. The first analysis
> also takes about a minute while the AI model loads; after that, results appear in a few seconds.

1. **Sign in.** Enter the evaluation activation code provided with our submission (format `MVAI-XXXX-XXXX-XXXX-XXXX`),
   keep **Remember this device for 30 days** ticked, and click **Activate**. The sidebar now shows
   *Licensed to: Hackathon judges*, and refreshing the page keeps you signed in. See [Licensing](#licensing-activation-codes).
2. **Tissue analysis → "Or try a sample".** Click **Colorectal adenoca…** (colorectal adenocarcinoma epithelium):
   expect **Tumour tissue detected** with *Confidence: High*, the tumour probability and predicted tissue tiles, the
   original image next to its **Grad-CAM overlay**, and calibrated scores for all 9 tissue types.
3. Open **Try another sample** (below the result) and click **Normal colon mucosa** or **Adipose**: expect
   **No tumour tissue detected**.
4. Click **Mosaic 16 patches tu…**: the image is scanned as 16 tiles; the 4 tumour patches on the diagonal are
   flagged (*Tumour tiles: 4 of 16*) and highlighted in the overlay.
5. **Upload** any grayscale picture (e.g. a chest X-ray): expect **Not assessed** with the reason. The model refuses
   to guess outside its domain.
6. Click **Discuss with the AI Assistant**: the assistant opens with the analysis attached and explains it, including
   its uncertainty. Ask a follow-up, switch to **Tissue analysis** and back; the chat is kept.
7. On the **AI Assistant** page, click one of the suggested questions, then try a non-medical request
   (e.g. "write a poem"): the assistant politely declines, because it answers medical questions only.
8. Open **Book an appointment**: select a specialist, choose **Urgent**, fill in the short form and **Send request**:
   it goes to the top of the line (*number 1*). Then sign out and sign in with the **coordinator code** provided with
   our submission: the **Triage queue** lists requests urgent-first; open **Schedule or decline** and **Confirm
   appointment**. Sign in again with the first code: *My requests* shows the confirmed date, time and room.
9. In the sidebar, open **Model card**, and see the [results table](#results-same-900-crc-val-he-7k-images-100-per-class-50-patients-never-seen-in-training)
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
- **Remember this device** (on by default): after a successful code, the browser keeps a signed token in its local
  storage for 30 days (never past the licence's expiry), so a refresh does not ask for the code again. (A cookie is
  not used: Streamlit Community Cloud's proxy does not pass cookies to apps.) On a new visit the page hands the token
  to the server once and removes it from the address. The token holds no activation code, cannot be forged without
  `ACTIVATION_SECRET`, and is re-checked every time, so revoking or expiring a licence also signs out remembered
  devices. **Sign out** deletes it.

## Hospital appointments and triage

**Book an appointment** lets users request an **in-person consultation** with a hospital specialist (gastrointestinal
pathologist, digital pathology & AI specialist, colorectal surgeon, gastroenterologist). Each request has an
urgency, and the queue is ordered **urgent → soon → routine**, then by time of request:

| Urgency | Target | Typical use |
|---|---|---|
| Urgent | within 48 hours | Suspected cancer or a result that could change treatment soon |
| Soon | within 2 weeks | Needs specialist review, no immediate risk |
| Routine | within 6 weeks | Second opinion, follow-up, questions |

The app *suggests* an urgency from an attached analysis (e.g. *Urgent* when tumour tissue was detected); the requester
decides and the hospital triages. Users see their **place in the line**, and the confirmed date, time and room.
Hospital **coordinators** sign in with a licence that has `role = "coordinator"` and get a **Triage queue** page to
confirm, decline or complete requests. A banner reminds users that emergencies need the emergency number, not a
booking. Only a short text summary of an analysis is shared, never images; the form asks for an internal patient
reference rather than names.

**Storage: Supabase** (free hosted database), so requests survive restarts and are shared by users and coordinators:

1. Create a free project at [supabase.com](https://supabase.com).
2. In the project, open **SQL Editor → New query**, paste the contents of `tools/supabase_schema.sql`, and click
   **Run**. This creates the `appointments` table with row level security on, so the public key cannot read it.
3. Open **Project Settings → API** and copy the **Project URL** and the **service_role** key (secret, server side).
4. Add to Streamlit secrets:
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "service-role key"
   HOSPITAL_NAME = "Your hospital name"        # optional, shown on the page
   ```

Without Supabase, the app uses an in-memory demo store (requests last until the app restarts), which is enough to
try the whole flow. A coordinator code is issued like any other, with `--role coordinator`:

```bash
python tools/make_activation_code.py --org "City Hospital, Outpatient coordination" --role coordinator
```

## Pages

| Page | What it does |
|---|---|
| **Sign in** | Licence activation with an activation code; optional *Remember this device for 30 days*. Shown until a valid code is entered. |
| **Tissue analysis** | **Upload** an image or pick one under **Or try a sample** → finding (*Tumour tissue detected* / *No tumour tissue detected* / *Not assessed*), tumour probability, predicted tissue, calibrated scores for all 9 classes, **Why this confidence**, the original image next to a semi-transparent **Grad-CAM overlay**, **Report** (JSON) and **Overlay** (PNG) downloads, and **Discuss with the AI Assistant**. Large images are scanned tile by tile. Sidebar: **Previous analyses**, **Analysis settings** (mode, tile size, tumour tiles needed, heatmap opacity) and **Model card**. |
| **Book an appointment** | Request an in-person consultation with a hospital specialist: urgency (Urgent / Soon / Routine, suggested from an attached analysis), reason, contact, preferred days, internal patient reference, optional image-free analysis summary. **My requests** shows status, place in the line, and the confirmed date, time and room. |
| **Triage queue** *(coordinators only)* | All requests, urgent first then oldest first, with counts per urgency; confirm a date, time and room, decline with a note, or mark as completed. |
| **AI Assistant** | ChatGPT-style chat, **medical and health questions only**. Suggested questions, **Attach an analysis to your next message**, or attach your own images with **+**. Several chats (**New chat**), kept while you switch pages; **Export chat** as Markdown; **Connection → Test connection**. |

The 9 classes (NCT-CRC-HE-100K): adipose tissue, background, debris/necrosis, lymphocytes, mucus, smooth muscle,
normal colon mucosa, cancer-associated stroma, **colorectal adenocarcinoma epithelium (tumour)**.

---

 The model, and why it was chosen

 Options evaluated

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

Results: same 900 CRC-VAL-HE-7K images (100 per class, 50 patients never seen in training)

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
2. `streamlit run app.py`. If licensing is configured in `.streamlit/secrets.toml`, sign in with a code from
   `tools/make_activation_code.py`; otherwise the app runs in demo mode without sign-in. Then, on **Tissue analysis**:
   - under **Or try a sample**, click **Colorectal adenoca…**: expect *Tumour tissue detected*, high confidence, and
     the overlay tinting the epithelium;
   - under **Try another sample**, click **Normal colon mucosa** and **Adipose**: expect *No tumour tissue detected*;
   - click **Mosaic 16 patches tu…**: expect a tile scan of 16 tiles, with the 4 tumour tiles on the diagonal highlighted;
   - **Upload** a chest X-ray or any grayscale image: expect *Not assessed* with an explanation;
   - in the sidebar, open **Analysis settings** and move **Heatmap opacity**: the overlay changes, and untinted tissue
     keeps its original colours.
3. Click **Discuss with the AI Assistant**: the assistant opens with the analysis attached and explains it. Ask a
   follow-up, switch back to **Tissue analysis** and return: the chat is still there.
4. On the **AI Assistant** page, click a suggested question, ask a medical question of your own, attach a picture with
   **+**, and check that a non-medical request is politely declined.
5. Without AI keys in `secrets.toml`, the assistant shows the offline notice, and tissue analysis keeps working.
6. Refresh the page after signing in (with *Remember this device* ticked): you stay signed in. **Sign out** returns to
   the sign-in page.

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

**Data and scope**
- The classifier covers **colorectal tissue only** (9 tissue types). Other organs, other tumour types, polyps and
  adenomas, tumour grading, staging and molecular subtypes are outside its training.
- Training data (NCT-CRC-HE-100K) comes from one German centre (NCT Heidelberg). The external test set
  (CRC-VAL-HE-7K, 50 patients) is from the same institution, so it does not prove performance at other hospitals.

**Robustness**
- The model expects patches of about 224 × 224 px at ~20× magnification. Screenshots or whole-slide overviews at
  unknown magnification are scanned tile by tile; this tile scan and its "tumour tiles needed" rule are heuristics
  that were not validated at slide level.
- *Cancer-associated stroma* and *debris* are the classes most often confused.
- The image check that rejects non-H&E images (e.g. X-rays) is a simple colour heuristic and can be fooled.

**Explanations**
- Grad-CAM shows which regions influenced the model, not proof of disease. The heatmap has low resolution
  (14 × 14 grid per patch), so it highlights areas, not individual cells.

**AI Assistant**
- Answers come from general-purpose language models (OpenAI, Google Gemini). They are not validated for pathology,
  can be wrong or inconsistent, With continued development, domain-specific training, and rigorous validation using expert-annotated pathology datasets, the system can be progressively improved toward greater reliability and clinical validation.
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
- Add uncertainty estimation and out-of-distribution detection, so the app can say "this image is unlike anything
  I was trained on" more reliably than the current colour check.
- Extend beyond tissue type: tumour grading, MSI/MMR status prediction, and polyp classification.

**Whole-slide support**
- Read whole-slide image formats (SVS, NDPI) with OpenSlide, detect tissue automatically, and show a slide-level
  tumour map instead of fixed tiles.
  
**Explanations and assistant**
- Ground the assistant's answers in cited sources (retrieval from pathology guidelines and papers), and evaluate
  its answers with pathologists.
- Offer a fully local, open-source vision-language model option, so no image leaves the computer.


## Licences

Phikon weights: Owkin non-commercial licence (research use). NCT-CRC-HE-100K / CRC-VAL-HE-7K: CC BY 4.0 (Kather et al.,
2019). Grad-CAM: Selvaraju et al., 2017.
