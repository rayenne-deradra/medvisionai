"""Study & benchmarks: how each model was chosen and validated (brain MRI study tables and figures, colorectal
robustness results stored with the classifier heads)."""
from __future__ import annotations

import csv
import html

import streamlit as st

from medvision.brain import CLASS_NAMES, GRAPHS_DIR, REPORTS_DIR
from medvision.config import MODELS_DIR
from medvision.ui.theme import page_head_html, section_html

e = html.escape


@st.cache_data(show_spinner=False)
def read_csv(name: str) -> list[dict]:
    with (REPORTS_DIR / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@st.cache_data(show_spinner=False)
def head_meta(fname: str) -> dict:
    import torch
    return torch.load(MODELS_DIR / fname, map_location="cpu", weights_only=False).get("meta", {})


def pct(v) -> str:
    return f"{float(v):.1%}" if v not in ("", None) else "—"


def num(v, d=3) -> str:
    return f"{float(v):.{d}f}" if v not in ("", None) else "—"


def table(headers: list[str], rows: list[list[str]], bold: int | None = None) -> str:
    """HTML table in the app's style; columns after the first are numbers. `bold` marks a row."""
    head = "".join(f'<th class="{"num" if i else ""}">{e(h)}</th>' for i, h in enumerate(headers))
    body = "".join(f'<tr class="{"sel" if i == bold else ""}">' +
                   "".join(f'<td class="{"num" if j else ""}">{c}</td>' for j, c in enumerate(r)) + "</tr>"
                   for i, r in enumerate(rows))
    return f'<table class="mv-table"><tr>{head}</tr>{body}</table>'


def card(key: str, label: str, content: str, foot: str = "") -> None:
    with st.container(key=key):
        st.markdown(f'<div class="mv-label">{e(label)}</div>{content}' +
                    (f'<div class="mv-foot">{foot}</div>' if foot else ""), unsafe_allow_html=True)


def kpis(items: list[tuple[str, str]]) -> None:
    st.markdown('<div class="mv-kpis" style="margin:0 0 6px">' + "".join(
        f'<div class="mv-kpi"><div class="k">{e(k)}</div><div class="v big">{v}</div></div>' for k, v in items)
        + "</div>", unsafe_allow_html=True)


st.markdown(page_head_html("Validation & comparative study", "Study & benchmarks",
                           "How each model was chosen and how it performs on held-out data. All numbers come from "
                           "the evaluation files shipped with the models."), unsafe_allow_html=True)
brain_tab, crc_tab = st.tabs(["Brain tumour MRI", "Colorectal tissue"])

# ----------------------------------------------------------------------------- brain MRI
with brain_tab:
    summary = read_csv("cnn_summary.csv")[0]
    seg = {r["model_name"]: r for r in read_csv("segmentation_model_benchmark.csv")}
    classical = sorted(read_csv("model_comparison_table.csv"), key=lambda r: -float(r["f1_score"]))
    kpis([("Ensemble test accuracy", pct(summary["accuracy"])), ("Ensemble macro-F1", num(summary["f1"])),
          ("Random Forest F1", num(classical[0]["f1_score"])),
          ("Deployed U-Net Dice", num(seg["unet_small"]["val_best_dice_tta"], 2))])
    st.caption("BRISC 2025: 10,793 T1 MRI slices (glioma, meningioma, pituitary tumour, no tumour); "
               "the test split (1,000 slices) was never used for training or model selection.")

    st.markdown(section_html("Deep-learning classifiers", "4 classes · test split"), unsafe_allow_html=True)
    c1, c2 = st.columns([1.35, 1], gap="medium")
    with c1:
        rows = [["EfficientNet-B0 · 5-fold ensemble", pct(summary["accuracy"]), "—", num(summary["f1"])]]
        rows += [[e(r["backbone_name"].replace("efficientnet_b0", "EfficientNet-B0").replace("convnext_tiny", "ConvNeXt-Tiny")
                    .replace("resnet18", "ResNet-18")), pct(r["test_accuracy"]), pct(r["test_accuracy_tta"]),
                  num(r["test_macro_f1"])] for r in read_csv("cnn_backbone_benchmark.csv")]
        card("mv_bench_a", "CNN backbones", table(["Model", "Accuracy", "With flip TTA", "Macro-F1"], rows, bold=0),
             "The ensemble averages five EfficientNet-B0 models from 5-fold cross-validation (weighted focal loss).")
    with c2:
        rows = [[e(CLASS_NAMES[r["label"]]), num(r["precision"]), num(r["recall"]),
                 num(r["f1-score"]), f'{float(r["support"]):.0f}'] for r in read_csv("cnn_classification_report.csv")
                if r["label"] in ("glioma", "meningioma", "pituitary", "no_tumor")]
        card("mv_bench_b", "Ensemble per class", table(["Class", "Prec.", "Recall", "F1", "n"], rows))

    st.markdown(section_html("Classical radiomics and segmentation", "tumour vs no tumour · lesion masks"),
                unsafe_allow_html=True)
    c1, c2 = st.columns([1.35, 1], gap="medium")
    with c1:
        rows = [[e(r["model"]), pct(r["accuracy"]), num(r["f1_score"]), num(r["auc_roc"]), num(r["cv_mean_f1"])]
                for r in classical]
        card("mv_bench_c", "Classical models on 7 image features",
             table(["Model", "Accuracy", "F1", "AUC", "CV F1"], rows, bold=0),
             "Random Forest is the deployed classical model. Gradient Boosting is not run in the app: its saved "
             "file needs an older scikit-learn.")
    with c2:
        rows = [[e(n.replace("unet_small", "U-Net small (deployed)").replace("deeplabv3_resnet50", "DeepLabV3-ResNet50")),
                 num(r["val_best_dice_no_tta"]), num(r["val_best_dice_tta"]), num(r["val_best_threshold_tta"], 2)]
                for n, r in seg.items()]
        card("mv_bench_d", "Segmentation (validation Dice)", table(["Model", "Dice", "Dice TTA", "Thr."], rows, bold=1),
             "The app ships the small U-Net (2 MB) for CPU speed; DeepLabV3 outlines lesions more accurately.")

    st.markdown(section_html("Figures", "from the comparative study"), unsafe_allow_html=True)
    FIGURES = [
        ("class_distribution.png", "Class distribution"), ("plane_distribution.png", "Anatomical planes"),
        ("sample_mri_grid.png", "Sample MRI slices"), ("sample_mask_overlay_grid.png", "Ground-truth tumour masks"),
        ("cnn_training_curves.png", "CNN training curves"), ("cnn_confusion_matrix.png", "Ensemble confusion matrix"),
        ("saliency_examples.png", "CNN saliency examples"), ("segmentation_examples.png", "Segmentation examples"),
        ("segmentation_training_curves.png", "Segmentation training curves"),
        ("model_comparison_barplot.png", "Classical model comparison"), ("roc_curves.png", "Classical ROC curves"),
        ("confusion_matrices.png", "Classical confusion matrices"),
        ("random_forest_feature_importance.png", "Random Forest feature importance"),
        ("tumor_area_by_class_boxplot.png", "Tumour area by class"),
    ]
    with st.container(key="mv_graphs"):
        cols = st.columns(2, gap="medium")
        for i, (f, caption) in enumerate(x for x in FIGURES if (GRAPHS_DIR / x[0]).exists()):
            with cols[i % 2]:
                st.markdown(f'<div class="mv-label">{e(caption)}</div>', unsafe_allow_html=True)
                st.image(str(GRAPHS_DIR / f), width="stretch")

# ----------------------------------------------------------------------------- colorectal
with crc_tab:
    phikon, lunit = head_meta("crc_head_phikon.pt"), head_meta("crc_head_lunit_vits8.pt")
    t = phikon.get("test", {})
    kpis([("9-class accuracy", pct(t.get("accuracy_9class"))), ("Macro-F1", num(t.get("macro_f1_9class"))),
          ("Tumour recall", pct(t.get("tumor_recall"))), ("Tumour precision", pct(t.get("tumor_precision")))])
    st.caption(f"Test set: {phikon.get('test_setup', 'CRC-VAL-HE-7K')}. Phikon (Owkin ViT-B/16) is the deployed "
               "backbone; Lunit DINO ViT-S/8 was evaluated on the same images.")
    st.markdown(section_html("Robustness", "accuracy · tumour recall under image changes"), unsafe_allow_html=True)
    conditions = list(phikon.get("robustness", {}))
    rows = []
    for c in conditions:
        p, l = phikon["robustness"][c], lunit.get("robustness", {}).get(c, {})
        rows.append([e(c.capitalize()), pct(p.get("accuracy_9class")), pct(p.get("tumor_recall")),
                     pct(l.get("accuracy_9class")), pct(l.get("tumor_recall"))])
    card("mv_bench_crc", "Phikon (selected) vs Lunit ViT-S/8",
         table(["Condition", "Phikon acc.", "Phikon recall", "Lunit acc.", "Lunit recall"], rows),
         "Phikon keeps the highest tumour recall on compressed and web-like images, which is what most uploads look "
         "like. Only a linear head (9 × 768 weights) was trained; the backbone is frozen.")
