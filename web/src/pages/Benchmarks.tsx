import { useEffect, useState } from "react";
import { api, type Report } from "../api";
import { PageHead, Reveal, Section } from "../components/ui";

const p = (v: unknown) => (v === "" || v == null ? "—" : `${(Number(v) * 100).toFixed(1)}%`);
const n = (v: unknown, d = 3) => (v === "" || v == null ? "—" : Number(v).toFixed(d));
const BACKBONE: Record<string, string> = { efficientnet_b0: "EfficientNet-B0", convnext_tiny: "ConvNeXt-Tiny", resnet18: "ResNet-18" };

function Table({ head, rows, bold }: { head: string[]; rows: (string | number)[][]; bold?: number }) {
  return (
    <table className="t"><thead><tr>{head.map((h, i) => <th key={h} className={i ? "num" : ""}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i} className={i === bold ? "sel" : ""}>{r.map((c, j) => <td key={j} className={j ? "num" : ""}>{c}</td>)}</tr>)}</tbody></table>
  );
}

export default function Benchmarks() {
  const [data, setData] = useState<Report | null>(null);
  const [tab, setTab] = useState<"brain" | "crc">("brain");
  const [error, setError] = useState("");
  useEffect(() => { api.get<Report>("/api/benchmarks").then(setData).catch((e) => setError(e.message)); }, []);
  const b = data?.brain, c = data?.colorectal;
  return (
    <>
      <PageHead kicker="Validation & comparative study" title="Study & benchmarks">
        How each model was chosen and how it performs on held-out data. Every number comes from the evaluation files shipped with the models.
      </PageHead>
      <div className="tabs">
        <button className={tab === "brain" ? "on" : ""} onClick={() => setTab("brain")}>Brain tumour MRI</button>
        <button className={tab === "crc" ? "on" : ""} onClick={() => setTab("crc")}>Colorectal tissue</button>
      </div>
      {error && <div className="alert error">{error}</div>}
      {b && tab === "brain" && (
        <>
          <div className="counts">
            <div><b>{p(b.summary.accuracy)}</b><span>Ensemble test accuracy</span></div>
            <div><b>{n(b.summary.f1)}</b><span>Ensemble macro-F1</span></div>
            <div><b>{n(b.classical[0].f1_score)}</b><span>Random Forest F1</span></div>
            <div><b>{n(b.segmentation.find((s: Report) => s.model_name === "unet_small")?.val_best_dice_tta, 2)}</b><span>Deployed U-Net Dice</span></div>
          </div>
          <div className="muted small">BRISC 2025: 10,793 T1 slices; the 1,000-slice test split was never used for training or model selection.</div>
          <Section title="Deep-learning classifiers" note="4 classes · test split" />
          <div className="grid2">
            <Reveal className="card"><div className="label">CNN backbones</div>
              <Table head={["Model", "Accuracy", "Flip TTA", "Macro-F1"]} bold={0}
                rows={[["EfficientNet-B0 · 5-fold ensemble", p(b.summary.accuracy), "—", n(b.summary.f1)],
                  ...b.backbones.map((r: Report) => [BACKBONE[r.backbone_name] || r.backbone_name, p(r.test_accuracy), p(r.test_accuracy_tta), n(r.test_macro_f1)])]} />
              <div className="foot">The ensemble averages five EfficientNet-B0 models from 5-fold cross-validation (weighted focal loss).</div></Reveal>
            <Reveal className="card" delay={0.05}><div className="label">Ensemble per class</div>
              <Table head={["Class", "Prec.", "Recall", "F1", "n"]} rows={b.per_class.map((r: Report) => [r.label, n(r.precision), n(r.recall), n(r["f1-score"]), Number(r.support)])} /></Reveal>
          </div>
          <Section title="Classical radiomics and segmentation" note="tumour vs no tumour · lesion masks" />
          <div className="grid2">
            <Reveal className="card"><div className="label">Classical models on 7 image features</div>
              <Table head={["Model", "Accuracy", "F1", "AUC", "CV F1"]} bold={0}
                rows={b.classical.map((r: Report) => [r.model, p(r.accuracy), n(r.f1_score), n(r.auc_roc), n(r.cv_mean_f1)])} />
              <div className="foot">Random Forest is the deployed classical model; Gradient Boosting is not run (its saved file needs an older scikit-learn).</div></Reveal>
            <Reveal className="card" delay={0.05}><div className="label">Segmentation (validation Dice)</div>
              <Table head={["Model", "Dice", "Dice TTA", "Thr."]} bold={1}
                rows={b.segmentation.map((r: Report) => [r.model_name === "unet_small" ? "U-Net small (deployed)" : "DeepLabV3-ResNet50",
                  n(r.val_best_dice_no_tta), n(r.val_best_dice_tta), n(r.val_best_threshold_tta, 2)])} />
              <div className="foot">The app ships the 2 MB U-Net for CPU speed; DeepLabV3 outlines lesions more accurately.</div></Reveal>
          </div>
          <Section title="Figures" note="from the comparative study" />
          <div className="figgrid">
            {b.figures.map((f: Report, i: number) => (
              <Reveal key={f.url} delay={0.03 * (i % 2)}><figure><figcaption>Fig. {i + 1} — {f.title}</figcaption><img src={f.url} alt={f.title} loading="lazy" /></figure></Reveal>
            ))}
          </div>
        </>
      )}
      {c && tab === "crc" && (
        <>
          <div className="counts">
            <div><b>{p(c.test.accuracy_9class)}</b><span>9-class accuracy</span></div>
            <div><b>{n(c.test.macro_f1_9class)}</b><span>Macro-F1</span></div>
            <div><b>{p(c.test.tumor_recall)}</b><span>Tumour recall</span></div>
            <div><b>{p(c.test.tumor_precision)}</b><span>Tumour precision</span></div>
          </div>
          <div className="muted small">Test set: {c.test_setup}. Phikon (Owkin ViT-B/16) is deployed; Lunit DINO ViT-S/8 was evaluated on the same images.</div>
          <Section title="Robustness" note="accuracy · tumour recall under image changes" />
          <Reveal className="card"><div className="label">Phikon (selected) vs Lunit ViT-S/8</div>
            <Table head={["Condition", "Phikon acc.", "Phikon recall", "Lunit acc.", "Lunit recall"]}
              rows={Object.entries(c.robustness as Record<string, Report>).map(([k, v]) => [k[0].toUpperCase() + k.slice(1), p(v.phikon.accuracy_9class),
                p(v.phikon.tumor_recall), p(v.lunit.accuracy_9class), p(v.lunit.tumor_recall)])} />
            <div className="foot">Phikon keeps the highest tumour recall on compressed and web-like images, which is what most uploads look like.</div></Reveal>
        </>
      )}
    </>
  );
}
