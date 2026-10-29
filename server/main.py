"""MedVisionAI REST API (FastAPI). Serves the React frontend from web/dist and the models behind /api.

Run locally:   uvicorn server.main:app --reload --port 8000        (API docs at http://localhost:8000/docs)
Research prototype only. Not a medical device. Not for diagnosis.
"""
from __future__ import annotations

import base64
import csv
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Iterator, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

from server import settings

settings.export_to_env()

from medvision import DISCLAIMER, __version__  # noqa: E402
from medvision.analysis import AnalysisSettings, analyze  # noqa: E402
from medvision.appointments import (OPEN, SPECIALISTS, STATUSES, URGENCY, MemoryStore, StoreConflict, StoreError,  # noqa: E402
                                    SupabaseStore, case_summary, new_request, queue_position, sort_key,
                                    suggest_urgency)
from medvision.auth import (ActivationError, AttemptLimiter, Licence, make_device_token,  # noqa: E402
                            read_device_token, verify)
from medvision.brain import (CLASS_NAMES, GRAPHS_DIR, REPORTS_DIR, SAMPLES_DIR, BrainModelError,  # noqa: E402
                             BrainSettings, report_for_llm)
from medvision.classifier import ClassifierError  # noqa: E402
from medvision.config import ASSETS_DIR, EXAMPLES_DIR, LLM_IMAGE_MAX_SIDE, MAX_UPLOAD_MB, MODELS_DIR, ROOT  # noqa: E402
from medvision.imaging import ImageError, downscale, load_image, overlay_image, to_bytes  # noqa: E402
from medvision.llm import (PREFERRED_MODELS, SYSTEM_PROMPT, ChatMessage, LLMError, OpenAIProvider,  # noqa: E402
                           case_context, gemini_provider, pick_model, rank_gemini_models)
from medvision.llm.providers import DEFAULT_BASE_URL  # noqa: E402

WEB_DIST = ROOT / "web" / "dist"
HOSPITAL = settings.secret("HOSPITAL_NAME") or "Example University Hospital"

app = FastAPI(
    title="MedVisionAI API",
    version=__version__,
    summary="Clinical Intelligence Platform for medical imaging: brain tumour MRI and colorectal histopathology.",
    description=("Research prototype, not a medical device. Endpoints marked 🔒 need `Authorization: Bearer <token>` "
                 "from `POST /api/auth/activate` (unless licensing is switched off on the server)."),
)
origins = [o.strip() for o in (settings.secret("ALLOWED_ORIGINS") or "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

# ----------------------------------------------------------------------------- models (loaded once, lazily)
_lock = threading.Lock()
_models: dict = {}


def brain_engine():
    with _lock:
        if "brain" not in _models:
            from medvision.brain import BrainEngine
            _models["brain"] = BrainEngine()
        return _models["brain"]


def tissue_classifier():
    with _lock:
        if "crc" not in _models:
            from medvision.classifier import load_classifier
            _models["crc"] = load_classifier()
        return _models["crc"]


# ----------------------------------------------------------------------------- auth
DEMO = {"licence_id": "demo", "organisation": "Demo user", "plan": "Demo", "expires": None, "role": "user"}
_limiters: dict[str, dict] = {}


def _demo(visitor: str | None) -> dict:
    """Demo licence; each browser gets its own id so visitors never see each other's cases or referrals."""
    vid = "".join(c for c in (visitor or "") if c.isalnum())[:32]
    return DEMO | {"licence_id": f"demo-{vid}"} if vid else DEMO


def current_licence(authorization: str | None = Header(default=None),
                    x_visitor: str | None = Header(default=None)) -> dict:
    """🔒 dependency: the licence behind the bearer token (re-checked on every request)."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not settings.licensing_on() or (not token and settings.open_access()):
        return _demo(x_visitor)
    licence = read_device_token(token, settings.secret("ACTIVATION_SECRET") or "", settings.licences()) if token else None
    if licence is None:
        raise HTTPException(401, "Enter an activation code to use this feature.")
    return licence.to_dict()


def coordinator(licence: dict = Depends(current_licence)) -> dict:
    if licence.get("role") != "coordinator":
        raise HTTPException(403, "Only hospital coordinators can do this.")
    return licence


class ActivateBody(BaseModel):
    code: str = Field(..., max_length=60, examples=["MVAI-XXXX-XXXX-XXXX-XXXX"])


@app.post("/api/auth/activate", tags=["auth"])
def activate(body: ActivateBody, request: Request):
    """Exchange an activation code for a signed access token (valid 30 days, never past the licence expiry)."""
    if not settings.licensing_on():
        return {"token": "", "licence": DEMO}
    limiter = AttemptLimiter(_limiters.setdefault(request.client.host if request.client else "?", {}))
    if wait := limiter.locked_for():
        raise HTTPException(429, f"Too many attempts. Please wait {wait} seconds and try again.")
    secret = settings.secret("ACTIVATION_SECRET") or ""
    try:
        licence: Licence = verify(body.code, secret, settings.licences())
    except ActivationError as e:
        limiter.failed()
        raise HTTPException(400, str(e)) from e
    limiter.succeeded()
    return {"token": make_device_token(licence, secret), "licence": licence.to_dict()}


@app.get("/api/auth/me", tags=["auth"])
def me(licence: dict = Depends(current_licence)):
    """🔒 The licence the token belongs to."""
    return licence


# ----------------------------------------------------------------------------- platform info
@app.get("/api/health", tags=["platform"])
def health():
    return {"status": "ok", "version": __version__, "licensing": settings.licensing_on(), "ai": bool(_providers()),
            "persistent_appointments": store().persistent, "models_loaded": sorted(_models)}


@app.get("/api/config", tags=["platform"])
def config():
    """Public settings the frontend needs: licensing, hospital, specialists, urgency levels, disclaimer."""
    return {"licensing": settings.licensing_on(), "open_access": settings.open_access(), "ai": bool(_providers()), "hospital": HOSPITAL,
            "disclaimer": DISCLAIMER, "persistent_appointments": store().persistent,
            "specialists": [{"id": s, "badge": b, "title": t, "department": d, "focus": f}
                            for s, b, t, d, f in SPECIALISTS],
            "urgency": {k: {"priority": p, "label": lab, "target": tgt, "description": desc}
                        for k, (p, lab, tgt, desc) in URGENCY.items()},
            "statuses": STATUSES}


def _brain_label(path: Path) -> dict:
    parts = path.stem.replace("no_tumor", "no-tumour").split("_")
    truth = parts[0].replace("-", " ")
    return {"name": path.name, "label": truth.capitalize() + (" 2" if "_2_" in path.stem else ""), "truth": truth,
            "tag": parts[1], "url": f"/static/brain-samples/{path.name}"}


def _crc_label(path: Path) -> dict:
    label = path.stem.replace("test_", "").rsplit("_", 1)[0].replace("_", " ").replace("-", " ")
    mosaic = path.stem.startswith("mosaic")
    return {"name": path.name, "truth": label, "url": f"/static/crc-samples/{path.name}",
            "label": "16-patch mosaic" if mosaic else label.replace("colorectal adenocarcinoma epithelium",
                                                                    "adenocarcinoma").capitalize(),
            "tag": "tile scan" if mosaic else "224 px patch"}


@app.get("/api/samples", tags=["platform"])
def samples():
    """Real test images (true label known) to try both models."""
    images = lambda d: sorted(p for p in d.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))  # noqa: E731
    return {"brain": [_brain_label(p) for p in images(SAMPLES_DIR)],
            "colorectal": [_crc_label(p) for p in images(EXAMPLES_DIR)]}


def _csv(name: str) -> list[dict]:
    with (REPORTS_DIR / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@app.get("/api/benchmarks", tags=["platform"])
def benchmarks():
    """Validation results: BRISC 2025 brain MRI study and colorectal robustness (CRC-VAL-HE-7K). Public."""
    import torch

    def meta(fname):
        return torch.load(MODELS_DIR / fname, map_location="cpu", weights_only=False).get("meta", {})

    phikon, lunit = meta("crc_head_phikon.pt"), meta("crc_head_lunit_vits8.pt")
    figures = [("class_distribution.png", "Class distribution"), ("plane_distribution.png", "Anatomical planes"),
               ("sample_mri_grid.png", "Sample MRI slices"), ("sample_mask_overlay_grid.png", "Ground-truth tumour masks"),
               ("cnn_training_curves.png", "CNN training curves"), ("cnn_confusion_matrix.png", "Ensemble confusion matrix"),
               ("saliency_examples.png", "CNN saliency examples"), ("segmentation_examples.png", "Segmentation examples"),
               ("segmentation_training_curves.png", "Segmentation training curves"),
               ("model_comparison_barplot.png", "Classical model comparison"), ("roc_curves.png", "Classical ROC curves"),
               ("confusion_matrices.png", "Classical confusion matrices"),
               ("random_forest_feature_importance.png", "Random Forest feature importance"),
               ("tumor_area_by_class_boxplot.png", "Tumour area by class")]
    return {
        "brain": {"summary": _csv("cnn_summary.csv")[0], "backbones": _csv("cnn_backbone_benchmark.csv"),
                  "per_class": [dict(r, label=CLASS_NAMES.get(r["label"], r["label"]))
                                for r in _csv("cnn_classification_report.csv") if r["label"] in CLASS_NAMES],
                  "classical": sorted(_csv("model_comparison_table.csv"), key=lambda r: -float(r["f1_score"])),
                  "segmentation": _csv("segmentation_model_benchmark.csv"),
                  "figures": [{"url": f"/static/graphs/{f}", "title": t} for f, t in figures if (GRAPHS_DIR / f).exists()]},
        "colorectal": {"test": phikon.get("test", {}), "test_setup": phikon.get("test_setup", ""),
                       "robustness": {c: {"phikon": v, "lunit": lunit.get("robustness", {}).get(c, {})}
                                      for c, v in phikon.get("robustness", {}).items()}},
    }


# ----------------------------------------------------------------------------- analysis
_cases: OrderedDict[str, dict] = OrderedDict()     # recent cases for the assistant and referrals (in memory)


def _keep(case: dict) -> None:
    _cases[case["id"]] = case
    while len(_cases) > 300:
        _cases.popitem(last=False)


def _case(case_id: str | None, licence: dict) -> dict | None:
    case = _cases.get(case_id or "")
    return case if case and case["licence_id"] == licence["licence_id"] else None


def _data_url(img: Image.Image, fmt: str = "JPEG") -> str:
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(to_bytes(img, fmt)).decode()


async def _input(file: UploadFile | None, sample: str | None, folder: Path) -> tuple[Image.Image, str]:
    if file is not None:
        data, name = await file.read(), file.filename or "image"
    elif sample:
        path = folder / Path(sample).name
        if not path.is_file():
            raise HTTPException(404, "Sample not found.")
        data, name = path.read_bytes(), path.name
    else:
        raise HTTPException(400, "Upload an image or choose a sample.")
    try:
        return load_image(data, MAX_UPLOAD_MB), Path(name).name[:80]
    except ImageError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/analyze/brain", tags=["analysis"])
async def analyze_brain(file: UploadFile | None = File(None), sample: str | None = Form(None),
                        backbone: Literal["ensemble", "efficientnet_b0", "convnext_tiny", "resnet18"] = Form("ensemble"),
                        plane: Literal["auto", "axial", "coronal", "sagittal"] = Form("auto"),
                        threshold: float = Form(0.35, ge=0.05, le=0.95), tta: bool = Form(True),
                        force: bool = Form(False), licence: dict = Depends(current_licence)):
    """🔒 Brain MRI slice → 4-class CNN ensemble, U-Net lesion mask, saliency, classical radiomics, triage score."""
    img, name = await _input(file, sample, SAMPLES_DIR)
    try:
        result = brain_engine().analyze(img, BrainSettings(backbone, plane, threshold, tta, force), name)
    except BrainModelError as e:
        raise HTTPException(503, str(e)) from e
    images = {k: downscale(Image.fromarray(v), 900) for k, v in result.images.items()}
    case = {"id": uuid.uuid4().hex[:12], "modality": "brain_mri", "licence_id": licence["licence_id"],
            "report": result.report, "report_llm": report_for_llm(result.report),
            "llm_images": [to_bytes(downscale(images[k], LLM_IMAGE_MAX_SIDE), "JPEG") for k in ("original", "overlay")
                           if k in images]}
    _keep(case)
    return {"case_id": case["id"], "report": result.report,
            "images": {k: _data_url(v, "PNG" if k == "mask" else "JPEG") for k, v in images.items()}}


@app.post("/api/analyze/colorectal", tags=["analysis"])
async def analyze_colorectal(file: UploadFile | None = File(None), sample: str | None = Form(None),
                             mode: Literal["Auto", "Single patch", "Tile scan"] = Form("Auto"),
                             tile_size: int | None = Form(None, ge=64, le=2048),
                             min_tumor_fraction: float = Form(0.10, ge=0.01, le=1.0),
                             alpha: float = Form(0.5, ge=0.1, le=0.9), force: bool = Form(False),
                             licence: dict = Depends(current_licence)):
    """🔒 H&E image → 9-class colorectal tissue classification, calibrated confidence, Grad-CAM overlay."""
    img, name = await _input(file, sample, EXAMPLES_DIR)
    try:
        result = analyze(img, tissue_classifier(),
                         AnalysisSettings(mode=mode, tile_size=tile_size, min_tumor_fraction=min_tumor_fraction,
                                          force_out_of_scope=force), name)
    except ClassifierError as e:
        raise HTTPException(503, str(e)) from e
    display = downscale(img, 900)
    report = result.report.to_dict() | {"modality": "colorectal"}
    images = {"original": display}
    if result.cam is not None:
        images["overlay"] = overlay_image(display, result.cam, alpha)
    llm_view = downscale(img, LLM_IMAGE_MAX_SIDE)
    llm_images = [to_bytes(llm_view, "JPEG")]
    if result.cam is not None:
        llm_images.append(to_bytes(overlay_image(llm_view, result.cam, 0.5), "JPEG"))
    case = {"id": uuid.uuid4().hex[:12], "modality": "colorectal", "licence_id": licence["licence_id"],
            "report": report, "report_llm": result.report.to_llm_dict() | {"modality": "colorectal"},
            "llm_images": llm_images}
    _keep(case)
    return {"case_id": case["id"], "report": report, "images": {k: _data_url(v) for k, v in images.items()}}


# ----------------------------------------------------------------------------- AI assistant
_provider_cache: dict = {}


def _providers() -> list[OpenAIProvider]:
    """OpenAI first, then up to six Gemini models (each fails over quickly). Model lists are read once."""
    out = []
    key = settings.secret("OPENAI_API_KEY")
    if key and not _provider_cache.get("openai_off"):
        base = settings.secret("OPENAI_BASE_URL", DEFAULT_BASE_URL)
        if "openai_model" not in _provider_cache:
            try:
                _provider_cache["openai_model"] = settings.secret("OPENAI_MODEL") or pick_model(
                    OpenAIProvider(key, "", base).list_models()) or PREFERRED_MODELS[0]
            except LLMError:
                _provider_cache["openai_model"] = PREFERRED_MODELS[0]
        out.append(OpenAIProvider(key, _provider_cache["openai_model"], base))
    gkey = settings.secret("GEMINI_API_KEY")
    if gkey:
        if "gemini_models" not in _provider_cache:
            models = [settings.secret("GEMINI_MODEL")] if settings.secret("GEMINI_MODEL") else []
            if not models:
                try:
                    ranked = rank_gemini_models(gemini_provider(gkey, "").list_models())
                    models = [m for m in ranked if "lite" not in m][:3] + [m for m in ranked if "lite" in m][:3]
                except LLMError:
                    models = []
            _provider_cache["gemini_models"] = models or ["gemini-flash-latest"]
        ms = _provider_cache["gemini_models"]
        out += [gemini_provider(gkey, m, attempts=1 if i < len(ms) - 1 else 2) for i, m in enumerate(ms)]
    return out


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=8000)


class ChatBody(BaseModel):
    messages: list[ChatTurn] = Field(..., min_length=1, max_length=40)
    case_id: str | None = Field(None, description="Attach an analysed case to the last user message")
    images: list[str] = Field(default_factory=list, max_length=4, description="Extra images as data URLs")


@app.post("/api/chat", tags=["assistant"])
def chat(body: ChatBody, licence: dict = Depends(current_licence)):
    """🔒 Streams the assistant's answer as plain text. Medical and health questions only."""
    providers = _providers()
    if not providers:
        raise HTTPException(503, "The AI Assistant is offline: no OPENAI_API_KEY or GEMINI_API_KEY is configured.")
    msgs = [ChatMessage(m.role, m.content) for m in body.messages[-16:]]
    while msgs and msgs[0].role != "user":
        msgs.pop(0)
    if not msgs or msgs[-1].role != "user":
        raise HTTPException(400, "The last message must come from the user.")
    last = msgs[-1]
    case = _case(body.case_id, licence)
    if case:
        last.text = (last.text or "Please explain this MedVisionAI result.") + "\n\n" + case_context(case["report_llm"])
        last.images += case["llm_images"]
    for url in body.images:
        try:
            raw = base64.b64decode(url.split(",", 1)[-1])
            last.images.append(to_bytes(downscale(load_image(raw, MAX_UPLOAD_MB), LLM_IMAGE_MAX_SIDE), "JPEG"))
        except (ImageError, ValueError):
            pass

    errors = []
    for provider in providers:      # fail over until one provider starts answering
        stream = provider.stream(SYSTEM_PROMPT, msgs)
        try:
            first = next(stream)
        except StopIteration:
            errors.append(f"{provider.label}: empty answer")
            continue
        except LLMError as e:
            errors.append(str(e))
            if provider.name == "OpenAI" and ("no credits" in str(e) or "(401)" in str(e)):
                _provider_cache["openai_off"] = True
            continue

        def body_iter(first=first, stream=stream) -> Iterator[str]:
            yield first
            try:
                yield from stream
            except LLMError:
                yield "\n\n*(The answer was interrupted. Please try again.)*"

        return StreamingResponse(body_iter(), media_type="text/plain; charset=utf-8",
                                 headers={"X-Provider": provider.label.replace("·", "-").encode("ascii", "replace").decode(),
                                          "Cache-Control": "no-cache"})
    raise HTTPException(503, "No AI model could answer right now (overloaded or over quota). Please try again in a "
                             "minute. " + " | ".join(errors[:2]))


# ----------------------------------------------------------------------------- appointments
_store_cache: dict = {}


def store():
    if "s" not in _store_cache:
        url, key = settings.secret("SUPABASE_URL"), settings.secret("SUPABASE_KEY")
        _store_cache["s"] = SupabaseStore(url, key) if url and key else MemoryStore()
    return _store_cache["s"]


class AppointmentBody(BaseModel):
    specialist_id: str
    urgency: Literal["urgent", "soon", "routine"]
    reason: str = Field(..., max_length=2000)
    requester: str = Field(..., max_length=120)
    contact: str = Field(..., max_length=120)
    preferred: str = Field("", max_length=300)
    patient_ref: str = Field("", max_length=60)
    case_id: str | None = None
    consent: bool


class AppointmentUpdate(BaseModel):
    status: Literal["confirmed", "declined", "completed", "cancelled"]
    appointment_at: str | None = None
    location: str = Field("", max_length=200)
    staff_note: str = Field("", max_length=500)


def _with_position(rows: list[dict], everything: list[dict]) -> list[dict]:
    return [r | {"position": queue_position(everything, r["id"])} for r in rows]


@app.get("/api/appointments", tags=["appointments"])
def list_appointments(licence: dict = Depends(current_licence)):
    """🔒 Your requests with their place in the line; coordinators also get the whole triage queue."""
    try:
        rows = sorted(store().list(), key=sort_key)
    except StoreError as e:
        raise HTTPException(502, str(e)) from e
    out = {"mine": _with_position([r for r in rows if r["licence_id"] == licence["licence_id"]], rows)}
    if licence.get("role") == "coordinator":
        out["queue"] = _with_position(rows, rows)
    return out


@app.get("/api/appointments/suggest", tags=["appointments"])
def suggest(case_id: str, licence: dict = Depends(current_licence)):
    """🔒 Suggested urgency and the image-free summary for an analysed case."""
    case = _case(case_id, licence)
    if not case:
        raise HTTPException(404, "Case not found (cases are kept for this server session only).")
    return {"urgency": suggest_urgency(case["report"]), "summary": case_summary(case["report"])}


@app.post("/api/appointments", tags=["appointments"], status_code=201)
def create_appointment(body: AppointmentBody, licence: dict = Depends(current_licence)):
    """🔒 Request an in-person consultation. Urgent requests go to the top of the queue."""
    if not body.consent:
        raise HTTPException(400, "Please confirm the consent statement.")
    spec = next((s for s in SPECIALISTS if s[0] == body.specialist_id), None)
    if spec is None:
        raise HTTPException(400, "Unknown specialist.")
    case = _case(body.case_id, licence)
    try:
        row = new_request(licence_id=licence["licence_id"], organisation=licence.get("organisation", ""),
                          requester=body.requester, contact=body.contact, hospital=HOSPITAL, specialist=spec[2],
                          department=spec[3], urgency=body.urgency, reason=body.reason, preferred=body.preferred,
                          patient_ref=body.patient_ref, case_summary=case_summary(case["report"]) if case else "")
        store().add(row)
        return row | {"position": queue_position(store().list(), row["id"])}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except StoreError as e:
        raise HTTPException(502, str(e)) from e


@app.patch("/api/appointments/{request_id}", tags=["appointments"])
def update_appointment(request_id: str, body: AppointmentUpdate, licence: dict = Depends(current_licence)):
    """🔒 Coordinators confirm, decline or complete; the requester may cancel an open request."""
    try:
        row = next((r for r in store().list() if r["id"] == request_id), None)
        if row is None:
            raise HTTPException(404, "Request not found.")
        if body.status == "cancelled":
            if row["licence_id"] != licence["licence_id"] or row["status"] not in OPEN:
                raise HTTPException(403, "You can only cancel your own open requests.")
            return store().update(request_id, expect_status=row["status"], status="cancelled")
        if licence.get("role") != "coordinator":
            raise HTTPException(403, "Only hospital coordinators can do this.")
        fields = {"status": body.status, "staff_note": body.staff_note}
        if body.status == "confirmed":
            if not body.appointment_at:
                raise HTTPException(400, "Choose a date and time.")
            fields |= {"appointment_at": body.appointment_at, "location": body.location}
        return store().update(request_id, expect_status=row["status"], **fields)
    except StoreConflict as e:
        raise HTTPException(409, str(e)) from e
    except StoreError as e:
        raise HTTPException(502, str(e)) from e


# ----------------------------------------------------------------------------- static files and the React app
app.mount("/static/brain-samples", StaticFiles(directory=SAMPLES_DIR), name="brain-samples")
app.mount("/static/crc-samples", StaticFiles(directory=EXAMPLES_DIR), name="crc-samples")
app.mount("/static/graphs", StaticFiles(directory=GRAPHS_DIR), name="graphs")
app.mount("/static/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
if (WEB_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="web-assets")


@app.exception_handler(404)
async def not_found(request: Request, exc):
    """Unknown non-API paths return the React app, which has its own router."""
    if request.url.path.startswith(("/api/", "/static/")) or not (WEB_DIST / "index.html").is_file():
        detail = getattr(exc, "detail", "Not found")
        return JSONResponse({"detail": detail}, status_code=404)
    file = (WEB_DIST / request.url.path.lstrip("/")).resolve()     # root files of the build, e.g. /logo.svg
    if file.is_file() and WEB_DIST.resolve() in file.parents:
        return FileResponse(file)
    return FileResponse(WEB_DIST / "index.html")


@app.get("/", include_in_schema=False)
def index():
    if (WEB_DIST / "index.html").is_file():
        return FileResponse(WEB_DIST / "index.html")
    return {"name": "MedVisionAI API", "docs": "/docs", "note": "Build the frontend with `npm run build` in web/."}
