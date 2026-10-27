# MedVisionAI: Clinical Intelligence Platform for medical imaging

**Early detection saves lives, but only if every scan is read in time.** MedVisionAI gives medical images an AI second opinion in seconds. Each result comes with its confidence, a visual explanation, and an urgent-first referral to the right specialist.

We started with two very different kinds of image to show that the idea works:

- **Brain tumour MRI:** glioma, meningioma, pituitary tumour or no tumour. Comes with a lesion outline and a 0–100 triage score.
- **Colorectal pathology (H&E):** 9 tissue types, with tumour detection and a Grad-CAM heatmap.

> ⚠️ **Research prototype, not a medical device.** It is not clinically validated, and its results are not a diagnosis.

---

## For judges: try it 

**Live app:** https://rayenne-deradra--medvisionai.us-east.modal.run (nothing to install)
**API docs:** https://rayenne-deradra--medvisionai.us-east.modal.run/docs

> The app is serverless, so the first load can take about a minute while it starts. After that, results arrive in seconds.

1. **Platform:** open the live link. Every page can be browsed without signing in.
2. **Brain tumour MRI:** pick a sample, such as *Glioma*, and click **Analyse**. When asked, enter the **activation code provided with our submission**. You get the prediction, the vote of the CNN ensemble, the U-Net lesion outline, the saliency map and the triage score.
3. **Colorectal tissue:** run the *Adenocarcinoma* sample to see **Tumour tissue detected** with its Grad-CAM. Then run *16-patch mosaic*, which flags the 4 tumour tiles out of 16. If you upload an out-of-scope image, such as a chest X-ray, the result is **Not assessed**: the model does not guess.
4. **AI Assistant:** click **Discuss with the AI Assistant** on any result. It explains the case and its uncertainty, and it declines non-medical questions.
5. **Appointments:** refer a case as **Urgent** and it goes to the top of the queue. Sign in with the **coordinator code** to triage and confirm it.
6. **Study & benchmarks:** shows how the models were chosen and validated.

---

## Results (on test data the models never saw)

| Module | Model | Result |
|---|---|---|
| Brain MRI (BRISC 2025, 1,000 test slices) | 5-fold EfficientNet-B0 ensemble | **99.3% accuracy**, macro-F1 0.994 |
| | ConvNeXt-Tiny / ResNet-18 (compared live) | 97.7% / 96.5% |
| | U-Net lesion segmentation | Dice 0.64 (validation, TTA) |
| Colorectal (CRC-VAL-HE-7K, 50 unseen patients) | Phikon ViT foundation model + calibrated head | **95.1% accuracy, 100% tumour recall**, 97.1% precision |

The colorectal model also holds up under JPEG compression and blur: tumour recall stays at 99% under both. The full robustness study is on the *Study & benchmarks* page.

---

## How it's built

| Part | Stack |
|---|---|
| Frontend | React 18, TypeScript, Vite, Framer Motion |
| Backend | FastAPI REST API, documented at `/docs` |
| Models | PyTorch, timm (Phikon), torchvision, scikit-learn |
| Assistant | OpenAI, with Google Gemini as fallback; medical questions only |
| Data | Supabase (PostgreSQL) for referrals |
| Hosting | Modal (serverless), Docker |
| Access | Activation codes stored as HMAC hashes only, signed 30-day tokens, rate-limited sign-in |

Each imaging modality is a separate model plug-in. Adding a new one, such as chest X-ray, does not change the rest of the app.

## Run locally

```bash
cd medvisionai_chat
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn server.main:app --port 8000   # open http://localhost:8000
```

**Tests:** `pip install -r requirements-eval.txt`, then `pytest -q` (46 tests).

---

## Limitations

- These are single 2D images; the app does not handle 3D volumes or DICOM yet.
- Each model was trained on a single public dataset, so results at other hospitals are not proven.
- The triage score is a heuristic, not a validated clinical score.
- The assistant uses general-purpose LLMs, which can be wrong.

## What's next

Chest X-ray and CT with DICOM import, external validation, and a hospital pilot with a reader study against specialists. After that come more modalities (skin, retina, ultrasound) and the medical-device regulatory pathway.

## Team

- **[rayenne-deradra](https://github.com/rayenne-deradra):** colorectal pathology module, AI assistant, activation and appointments, the merged React + FastAPI platform, and deployment.
- **[Aiden8teen](https://github.com/Aiden8teen):** brain tumour MRI study and models (CNN ensemble, U-Net, classical models).


## Credits and licences

BRISC 2025 dataset · NCT-CRC-HE-100K and CRC-VAL-HE-7K (CC BY 4.0, Kather et al., 2019) · Phikon weights (Owkin, non-commercial research licence) · Grad-CAM (Selvaraju et al., 2017).
