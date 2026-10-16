"""MedVisionAI: multi-module tissue image explorer (research prototype).
Modules: colorectal tissue (9 types) and lymph node metastasis (cancer / non-cancer).
Not a medical device. Not for clinical use."""
import base64
import html
import io
import os
import time
from glob import glob

import numpy as np
import streamlit as st

import medvision_infer as mvi
from medvision_modules import LoadedModel

# ===================== SETTINGS: edit these lines =====================
HF_REPO_ID = "YOUR-USERNAME/YOUR-REPO"      # ONE Hugging Face model repo that holds both checkpoint files
MODULES = {
    "crc": {
        "title": "Colorectal tissue", "kind": "multiclass",
        "file": "model_v2_convnext_tiny_seed0.pt",          # exact file name in the Hugging Face repo
        "env": "MEDVISION_CRC_CKPT",                         # optional: local file for testing
        "results": "results_colorectal.json",                # optional: your results_v2_...json, renamed
        "examples": "examples",
        "task": "Names the tissue type of a small colorectal H&E patch (9 types), including tumor epithelium.",
        "data": "Trained on NCT-CRC-HE-100K patches (via PathMNIST, 64 x 64 px). Tested on separate patients.",
        "input": "Small H&E patch, best at about 64 px.",
    },
    "ln": {
        "title": "Lymph node metastasis", "kind": "binary",
        "file": "medvision_pcam_convnext_tiny.pt",          # exact file name printed by the PCam notebook
        "env": "MEDVISION_PCAM_CKPT",
        "results": None,
        "examples": "examples_pcam",
        "task": "Scores whether the centre of a lymph node patch contains metastatic tumor (Cancer or Non-cancer).",
        "data": "Trained on PatchCamelyon (96 x 96 px, slide-disjoint splits).",
        "input": "Small H&E patch, best at about 96 px.",
    },
}
# ======================================================================

TISSUE_HELP = {
    "adipose": "fat tissue", "background": "empty slide background", "debris": "cell debris or dead tissue",
    "lymphocytes": "immune cells", "mucus": "mucus", "smooth muscle": "smooth muscle tissue",
    "normal colon mucosa": "healthy lining of the colon", "cancer-associated stroma": "connective tissue around a tumor",
    "colorectal adenocarcinoma epithelium": "tumor cells (colorectal adenocarcinoma)",
}

st.set_page_config(page_title="MedVisionAI", page_icon="🔬", layout="wide")

CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.1rem; max-width: 1280px;}
.mv-header {background: linear-gradient(95deg,#0B3C5D 0%,#0F766E 100%); color: #fff; padding: 18px 24px;
  border-radius: 14px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;}
.mv-header h1 {margin: 0; font-size: 1.7rem; color: #fff; padding: 0;}
.mv-header .sub {opacity: .85; font-size: .95rem; margin-top: 2px;}
.mv-pill {background: rgba(255,255,255,.16); border-radius: 999px; padding: 6px 14px; font-size: .8rem;}
.mv-banner {background: #FFF7ED; border: 1px solid #FDBA74; color: #9A3412; padding: 10px 14px;
  border-radius: 10px; font-size: .88rem; margin-bottom: 14px;}
.mv-card {background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(15,23,42,.06); height: 100%;}
.mv-card h4 {margin: 0 0 6px 0; font-size: 1rem; color: #0B3C5D;}
.mv-muted {color: #64748B; font-size: .85rem;}
.mv-chip {display: inline-block; padding: 4px 14px; border-radius: 999px; font-weight: 700; font-size: .85rem;}
.chip-red {background: #FEE2E2; color: #991B1B;} .chip-green {background: #DCFCE7; color: #166534;}
.chip-amber {background: #FEF3C7; color: #92400E;} .chip-grey {background: #E2E8F0; color: #334155;}
.mv-big {font-size: 1.55rem; font-weight: 700; color: #0F172A; margin: 6px 0 2px 0; line-height: 1.2;}
.mv-bar-row {display: flex; align-items: center; gap: 10px; margin: 5px 0;}
.mv-bar-label {width: 46%; font-size: .86rem; color: #0F172A;}
.mv-bar-track {flex: 1; background: #E8EEF3; border-radius: 6px; height: 12px; overflow: hidden;}
.mv-bar-fill {height: 100%; border-radius: 6px;}
.mv-bar-val {width: 56px; text-align: right; font-size: .82rem; color: #475569; font-variant-numeric: tabular-nums;}
.mv-gauge {position: relative; height: 16px; background: linear-gradient(90deg,#DCFCE7,#FEF3C7,#FEE2E2);
  border-radius: 8px; margin: 10px 0 4px 0;}
.mv-gauge-fill {position: absolute; top: 0; left: 0; height: 100%; background: rgba(11,60,93,.28); border-radius: 8px;}
.mv-gauge-thr {position: absolute; top: -4px; width: 3px; height: 24px; background: #0B3C5D;}
.mv-step {text-align: center; padding: 6px 4px;}
.mv-step .n {display: inline-block; width: 30px; height: 30px; line-height: 30px; border-radius: 50%;
  background: #0F766E; color: #fff; font-weight: 700; margin-bottom: 6px;}
.mv-explain {background: #F0F9FF; border-left: 4px solid #0B3C5D; padding: 12px 16px; border-radius: 8px;
  font-size: .95rem; line-height: 1.55;}
.mv-note {color: #64748B; font-size: .8rem; margin-top: 8px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------- loading
@st.cache_resource(show_spinner="Loading the model (first start only)...")
def get_model(key):
    spec = MODULES[key]
    local = os.environ.get(spec["env"])
    if local:
        return LoadedModel.from_path(key, spec["kind"], local, spec["results"])
    if HF_REPO_ID.startswith("YOUR-"):
        raise mvi.InferenceError("Set HF_REPO_ID at the top of streamlit_app.py to your Hugging Face repo.")
    return LoadedModel.from_hub(key, spec["kind"], HF_REPO_ID, spec["file"], spec["results"])


@st.cache_data(show_spinner="Analyzing the image...", max_entries=40)
def run_analysis(key, data):
    return get_model(key).analyze(data)


# ----------------------------------------------------------------------------- helpers
def pretty(name):
    return name[:1].upper() + name[1:]


def to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def where(cy, cx):
    v = "upper" if cy < 0.4 else "lower" if cy > 0.6 else ""
    h = "left" if cx < 0.4 else "right" if cx > 0.6 else ""
    if not v and not h:
        return "the centre of the patch"
    return "the " + " ".join(x for x in (v, h) if x) + " part of the patch"


def confidence_level(lm, probs):
    if lm.threshold is not None:
        s, t = probs[lm.tumor_index], lm.threshold
        if s >= t:
            return ("High", "chip-red") if (s - t) / max(1 - t, 1e-6) >= 0.5 else ("Borderline", "chip-amber")
        return ("High", "chip-green") if (t - s) / max(t, 1e-6) >= 0.5 else ("Borderline", "chip-amber")
    top = float(np.max(probs))
    return ("High", "chip-grey") if top >= 0.8 else ("Moderate", "chip-amber") if top >= 0.6 else ("Low", "chip-amber")


def bars_html(lm, probs, pred):
    rows = ""
    for i in np.argsort(-probs):
        color = "#B91C1C" if i == lm.tumor_index else "#0F766E"
        weight = "700" if i == pred else "400"
        rows += (f'<div class="mv-bar-row"><div class="mv-bar-label" style="font-weight:{weight}">'
                 f'{html.escape(pretty(lm.names[i]))}</div><div class="mv-bar-track"><div class="mv-bar-fill" '
                 f'style="width:{probs[i] * 100:.1f}%;background:{color}"></div></div>'
                 f'<div class="mv-bar-val">{probs[i] * 100:.1f}%</div></div>')
    return rows


def explanation_lines(lm, a):
    pred, probs = a["pred"], a["probs"]
    name = lm.names[pred]
    out = []
    if lm.threshold is not None:
        s = probs[lm.tumor_index]
        verdict = "Cancer" if pred == lm.tumor_index else "Non-cancer"
        out.append(f"The model gives this patch a cancer score of **{s:.2f}**. The decision threshold is "
                   f"**{lm.threshold:.2f}** (chosen on separate validation data), so it reads the patch as **{verdict}**.")
    else:
        order = np.argsort(-probs)
        out.append(f"The model's best match is **{pretty(name)}** ({probs[pred]:.0%}), "
                   f"described as {TISSUE_HELP.get(name, 'a tissue type')}.")
        second = order[1]
        out.append(f"The closest alternative is {pretty(lm.names[second])} ({probs[second]:.0%}).")
    out.append(f"The heatmap shows it relied most on **{where(*a['cam_center'])}** when deciding for "
               f"*{pretty(name)}*.")
    if a["hidden_probs"] is not None and a["random_probs"] is not None:
        before, after = float(probs[pred]), float(a["hidden_probs"][pred])
        rand_after = float(a["random_probs"][:, pred].mean())
        out.append(f"**Stress test:** when that highlighted area is hidden, the score for {pretty(name)} goes from "
                   f"{before:.0%} to {after:.0%}. Hiding a random area of the same size gives {rand_after:.0%} on average.")
        drop, rand_drop = before - after, before - rand_after
        if drop > 0.15 and drop > 2 * max(rand_drop, 0.02):
            out.append("That drop is much larger than for random areas, so the highlighted area really carries the "
                       "evidence the model uses.")
        elif drop < 0.05:
            out.append("Hiding it changes little, so the model is using wider context or other cues. "
                       "Treat the heatmap with caution.")
        else:
            out.append("The effect is mixed: the highlighted area matters, but not much more than other areas.")
        if lm.decide(a["hidden_probs"]) != pred:
            out.append("Hiding that area would **change the decision**, which shows how much the result depends on it.")
    weak = lm.results.get("per_class_recall", {}).get(name)
    if weak is not None and weak < 0.9:
        out.append(f"**Known weakness:** on the independent test set this tissue type was recognised only "
                   f"{weak:.0%} of the time, and it is often mixed up with similar tissue.")
    return out


def md_to_html(text):
    t = html.escape(text)
    parts = t.split("**")
    t = "".join(p if i % 2 == 0 else f"<b>{p}</b>" for i, p in enumerate(parts))
    parts = t.split("*")
    return "".join(p if i % 2 == 0 else f"<i>{p}</i>" for i, p in enumerate(parts))


def build_report(spec, lm, a, lines, source_name):
    pred = a["pred"]
    verdict = pretty(lm.names[pred]) if lm.threshold is None else ("Cancer" if pred == lm.tumor_index else "Non-cancer")
    rows = "".join(f"<tr><td>{html.escape(pretty(lm.names[i]))}</td><td>{a['probs'][i] * 100:.1f}%</td></tr>"
                   for i in np.argsort(-a["probs"]))
    explain = "".join(f"<p>{md_to_html(l)}</p>" for l in lines)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>MedVisionAI report</title>
<style>body{{font-family:Arial,sans-serif;max-width:860px;margin:24px auto;color:#0f172a}}
h1{{color:#0B3C5D}} .warn{{background:#FFF7ED;border:1px solid #FDBA74;padding:10px;border-radius:8px;color:#9A3412}}
img{{border:1px solid #cbd5e1;border-radius:8px}} td,th{{border-bottom:1px solid #e2e8f0;padding:4px 10px;text-align:left}}
</style></head><body>
<h1>MedVisionAI analysis report</h1>
<div class="warn"><b>Research prototype. Not a medical device. Not for clinical use or diagnosis.</b>
A qualified pathologist must review any real case.</div>
<p>Module: <b>{html.escape(spec['title'])}</b> | Model: {html.escape(lm.arch)}, input {lm.size} px |
Source: {html.escape(str(lm.source))}<br>Image: {html.escape(source_name)} | Generated (UTC): {time.strftime('%Y-%m-%d %H:%M', time.gmtime())}</p>
<h2>Result: {html.escape(verdict)}</h2>
<p><img src="data:image/png;base64,{to_b64(a['image'].resize((256, 256)))}" width="256"> &nbsp;
<img src="data:image/png;base64,{to_b64(a['overlay'])}" width="256"></p>
<table><tr><th>Class</th><th>Model score</th></tr>{rows}</table>
<h2>Why the model says this</h2>{explain}
<p style="color:#64748b;font-size:12px">Scores are model outputs, not calibrated probabilities. The heatmap and the stress test
describe the behaviour of the model, not medical reasoning.</p></body></html>"""


def metric_row(label, value, ci=None):
    extra = f" [{ci[0]:.3f}, {ci[1]:.3f}]" if ci else ""
    return f"- {label}: **{value:.3f}**{extra}"


# ----------------------------------------------------------------------------- page
st.markdown("""
<div class="mv-header"><div><h1>🔬 MedVisionAI</h1>
<div class="sub">Tissue image explorer with visual explanations</div></div>
<div class="mv-pill">Research prototype</div></div>
<div class="mv-banner"><b>Not a medical device.</b> For research and demonstration only. Do not use it for diagnosis,
and do not upload images that can identify a patient. This app's code does not store uploaded images.</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Case panel")
    key = st.radio("1. Choose the module", list(MODULES), format_func=lambda k: MODULES[k]["title"])
    spec = MODULES[key]
    st.caption(spec["task"])
    st.markdown("**2. Provide an image**")
    uploaded = st.file_uploader("Upload a patch", type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"],
                                label_visibility="collapsed")
    ex_files = sorted(glob(os.path.join(spec["examples"], "*.png")))
    ex_map = {os.path.basename(p)[:-4].replace("_", " "): p for p in ex_files}
    choice = st.selectbox("...or pick an example (true label in the name)", ["(none)"] + list(ex_map)) if ex_map else "(none)"
    st.caption(spec["input"])

data, source_name = None, ""
if uploaded is not None:
    data, source_name = uploaded.getvalue(), uploaded.name
elif choice != "(none)":
    data, source_name = open(ex_map[choice], "rb").read(), choice

try:
    lm = get_model(key)
except mvi.InferenceError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"Could not start the model: {e}")
    st.stop()

if data is None:
    st.markdown("#### How it works")
    c1, c2, c3 = st.columns(3)
    for col, n, t, d in [(c1, 1, "Choose a module", "Pick the tissue type in the left panel."),
                         (c2, 2, "Add an image", "Upload a small H&E patch or try an example."),
                         (c3, 3, "Read the explanation", "See the result, the heatmap and a stress test of the evidence.")]:
        col.markdown(f'<div class="mv-card mv-step"><div class="n">{n}</div><br><b>{t}</b>'
                     f'<div class="mv-muted">{d}</div></div>', unsafe_allow_html=True)
    st.markdown("#### Available modules")
    cols = st.columns(len(MODULES))
    for col, (k, s) in zip(cols, MODULES.items()):
        col.markdown(f'<div class="mv-card"><h4>{html.escape(s["title"])}</h4>{html.escape(s["task"])}'
                     f'<div class="mv-muted" style="margin-top:8px">{html.escape(s["data"])}</div></div>',
                     unsafe_allow_html=True)
    st.markdown('<div class="mv-note">More modules can be added the same way: one trained model per tissue or cancer '
                'type, each with its own evaluation and its own limits.</div>', unsafe_allow_html=True)
else:
    try:
        a = run_analysis(key, data)
    except mvi.InferenceError as e:
        st.error(str(e))
        st.stop()
    pred, probs = a["pred"], a["probs"]
    is_tumor = pred == lm.tumor_index
    conf, conf_cls = confidence_level(lm, probs)
    lines = explanation_lines(lm, a)

    left, mid, right = st.columns([1, 1, 1.15])
    with left:
        st.markdown("**Input patch**")
        st.image(a["image"].resize((300, 300)), width=300)
    with mid:
        st.markdown("**Where the model looked**")
        st.image(a["overlay"], width=300)
        st.caption("Red and yellow: areas that raised the score of the predicted class.")
    with right:
        if lm.threshold is not None:
            headline = "Cancer" if is_tumor else "Non-cancer"
            s = float(probs[lm.tumor_index])
            detail = (f'<div class="mv-gauge"><div class="mv-gauge-fill" style="width:{s * 100:.1f}%"></div>'
                      f'<div class="mv-gauge-thr" style="left:{lm.threshold * 100:.1f}%"></div></div>'
                      f'<div class="mv-muted">cancer score {s:.3f} | threshold {lm.threshold:.3f} (dark marker)</div>')
        else:
            headline = pretty(lm.names[pred])
            detail = bars_html(lm, probs, pred)
        chip = "chip-red" if is_tumor else "chip-green"
        tag = "Tumor tissue" if is_tumor else "Non-tumor"
        st.markdown(f'<div class="mv-card"><span class="mv-chip {chip}">{tag}</span> '
                    f'<span class="mv-chip {conf_cls}">Confidence: {conf}</span>'
                    f'<div class="mv-big">{html.escape(headline)}</div>{detail}'
                    f'<div class="mv-note">Scores are model outputs, not calibrated probabilities.</div></div>',
                    unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Why this result", "Stress test", "Model and evaluation"])
    with tab1:
        st.markdown('<div class="mv-explain">' + "<br><br>".join(md_to_html(l) for l in lines) + "</div>",
                    unsafe_allow_html=True)
        st.markdown('<div class="mv-note">The heatmap and the stress test describe how the <b>model</b> behaves. '
                    'They are not a medical finding. A pathologist must review any real case.</div>',
                    unsafe_allow_html=True)
    with tab2:
        st.write("The model is run again with part of the image replaced by a neutral average colour.")
        c1, c2 = st.columns(2)
        if a["hidden_image"] is not None:
            c1.image(a["hidden_image"].resize((260, 260)), caption="Highlighted area hidden", width=260)
            c1.write(f"Score for {pretty(lm.names[pred])}: **{probs[pred]:.0%} to {a['hidden_probs'][pred]:.0%}**")
        if a["random_probs"] is not None:
            c2.write("Control: hiding random squares of the same size")
            c2.write(f"Average score for {pretty(lm.names[pred])}: **{a['random_probs'][:, pred].mean():.0%}** "
                     f"(range {a['random_probs'][:, pred].min():.0%} to {a['random_probs'][:, pred].max():.0%})")
    with tab3:
        st.write(f"**{spec['title']}**: {lm.arch}, input {lm.size} px.  \n{spec['data']}")
        st.write(f"Checkpoint: `{lm.source}`")
        if lm.meta.get("smoke_test"):
            st.error("This checkpoint comes from a SMOKE TEST on fake data. Do not use it.")
        tm, ci = lm.meta.get("test_metrics"), lm.meta.get("test_ci95", {})
        if tm:
            st.markdown("**Held-out test results (95% intervals in brackets):**")
            for k, label in [("recall", "Sensitivity (cancer found)"), ("specificity", "Specificity"),
                             ("auc", "ROC-AUC"), ("precision", "Precision"), ("f1", "F1")]:
                if k in tm:
                    st.markdown(metric_row(label, tm[k], ci.get(k)))
        res = lm.results.get("test")
        if res:
            st.markdown("**Independent test results:**")
            for k, label in [("acc_9class", "Accuracy (9 types)"), ("macro_f1_9class", "Macro F1"),
                             ("tumor_precision", "Tumor precision"), ("tumor_recall", "Tumor recall"),
                             ("tumor_auroc", "Tumor ROC-AUC")]:
                if k in res:
                    st.markdown(metric_row(label, res[k]))
            pcr = lm.results.get("per_class_recall", {})
            if pcr:
                weakest = sorted(pcr.items(), key=lambda kv: kv[1])[:3]
                st.markdown("Weakest tissue types (test recall): " +
                            ", ".join(f"{pretty(n)} {v:.0%}" for n, v in weakest))
        if not tm and not res:
            st.info("No evaluation file found for this module, so no numbers are shown.")
        st.markdown('<div class="mv-note">One test split. Patches from the same slides are correlated. '
                    'Other stains, scanners and image scales can give confident but wrong answers.</div>',
                    unsafe_allow_html=True)

    report = build_report(spec, lm, a, lines, source_name)
    st.download_button("Download report (HTML, printable to PDF)", report, file_name="medvisionai_report.html",
                       mime="text/html")
