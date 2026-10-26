import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { api, type Report } from "../api";
import { Empty, PageHead, SectionHead } from "../components/ui";

const p = (v: unknown) => (v === "" || v == null ? "—" : `${(Number(v) * 100).toFixed(1)}%`);
const n = (v: unknown, d = 3) => (v === "" || v == null ? "—" : Number(v).toFixed(d));
const BACKBONE: Record<string, string> = { efficientnet_b0: "EfficientNet-B0", convnext_tiny: "ConvNeXt-Tiny", resnet18: "ResNet-18" };

function Table({ head, rows, bold }: { head: string[]; rows: (string | number)[][]; bold?: number }) {
  return (
    <table className="tbl"><thead><tr>{head.map((h, i) => <th key={h} className={i ? "num" : ""}>{h}</th>)}</tr></thead>
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
      <PageHead icon={<BarChart3 size={16} />} eyebrow="Validation and comparative study" title="Study & benchmarks">
        How each model was chosen and how it performs on held-out data. Every number comes from the evaluation files shipped with the models.
      </PageHead>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "brain"} className={tab === "brain" ? "on" : ""} onClick={() => setTab("brain")}>Brain tumour MRI</button>
        <button role="tab" aria-selected={tab === "crc"} className={tab === "crc" ? "on" : ""} onClick={() => setTab("crc")}>Colorectal tissue</button>
      </div>
      {error && <div className="alert danger">{error}</div>}
      {!data && !error && <Empty title="Loading results" loading>Reading the evaluation tables.</Empty>}
      {b && tab === "brain" && (
        <>
          <div className="stats" style={{ marginTop: 0 }}>
            {[[p(b.summary.accuracy), "Ensemble test accuracy"], [n(b.summary.f1), "Ensemble macro-F1"], [n(b.classical[0].f1_score), "Random Forest F1 (tumour vs none)"],
              [n(b.segmentation.find((s: Report) => s.model_name === "unet_small")?.val_best_dice_tta, 2), "Deployed U-Net Dice"]]
              .map(([v, k]) => <div key={k} className="card stat"><b>{v}</b><span>{k}</span></div>)}
          </div>
          <p className="hint">BRISC 2025: 10,793 T1 slices. The 1,000-slice test split was never used for training or model selection.</p>
          <SectionHead title="Deep-learning classifiers" note="Four classes, test split" />
          <div className="grid-2">
            <div className="card"><h3 className="h3" style={{ marginBottom: 12 }}>CNN backbones</h3>
              <Table head={["Model", "Accuracy", "Mirror TTA", "Macro-F1"]} bold={0}
                rows={[["EfficientNet-B0, 5-fold ensemble", p(b.summary.accuracy), "—", n(b.summary.f1)],
                  ...b.backbones.map((r: Report) => [BACKBONE[r.backbone_name] || r.backbone_name, p(r.test_accuracy), p(r.test_accuracy_tta), n(r.test_macro_f1)])]} />
              <p className="hint">The ensemble averages five EfficientNet-B0 models from 5-fold cross-validation.</p></div>
            <div className="card"><h3 className="h3" style={{ marginBottom: 12 }}>Ensemble by class</h3>
              <Table head={["Class", "Precision", "Recall", "F1", "Slices"]} rows={b.per_class.map((r: Report) => [r.label, n(r.precision), n(r.recall), n(r["f1-score"]), Number(r.support)])} /></div>
          </div>
          <SectionHead title="Radiomics and segmentation" />
          <div className="grid-2">
            <div className="card"><h3 className="h3" style={{ marginBottom: 12 }}>Classical models on 7 image features</h3>
              <Table head={["Model", "Accuracy", "F1", "AUC", "CV F1"]} bold={0}
                rows={b.classical.map((r: Report) => [r.model, p(r.accuracy), n(r.f1_score), n(r.auc_roc), n(r.cv_mean_f1)])} />
              <p className="hint">Random Forest is deployed. Gradient Boosting is not run: its saved file needs an older scikit-learn.</p></div>
            <div className="card"><h3 className="h3" style={{ marginBottom: 12 }}>Segmentation, validation Dice</h3>
              <Table head={["Model", "Dice", "With TTA", "Threshold"]} bold={1}
                rows={b.segmentation.map((r: Report) => [r.model_name === "unet_small" ? "U-Net small (deployed)" : "DeepLabV3-ResNet50",
                  n(r.val_best_dice_no_tta), n(r.val_best_dice_tta), n(r.val_best_threshold_tta, 2)])} />
              <p className="hint">The 2 MB U-Net is deployed for CPU speed; DeepLabV3 outlines lesions more accurately.</p></div>
          </div>
          <SectionHead title="Figures" note="From the comparative study" />
          <div className="figs">
            {b.figures.map((f: Report) => <figure key={f.url}><figcaption>{f.title}</figcaption><img src={f.url} alt={f.title} loading="lazy" /></figure>)}
          </div>
        </>
      )}
      {c && tab === "crc" && (
        <>
          <div className="stats" style={{ marginTop: 0 }}>
            {[[p(c.test.accuracy_9class), "Nine-class accuracy"], [n(c.test.macro_f1_9class), "Macro-F1"], [p(c.test.tumor_recall), "Tumour recall"],
              [p(c.test.tumor_precision), "Tumour precision"]].map(([v, k]) => <div key={k} className="card stat"><b>{v}</b><span>{k}</span></div>)}
          </div>
          <p className="hint">Test set: {c.test_setup}. Phikon (Owkin ViT-B/16) is deployed; Lunit DINO ViT-S/8 was evaluated on the same images.</p>
          <SectionHead title="Robustness" note="Accuracy and tumour recall under image changes" />
          <div className="card">
            <Table head={["Condition", "Phikon accuracy", "Phikon recall", "Lunit accuracy", "Lunit recall"]}
              rows={Object.entries(c.robustness as Record<string, Report>).map(([k, v]) => [k[0].toUpperCase() + k.slice(1), p(v.phikon.accuracy_9class),
                p(v.phikon.tumor_recall), p(v.lunit.accuracy_9class), p(v.lunit.tumor_recall)])} />
            <p className="hint">Phikon keeps the highest tumour recall on compressed and web-like images, which is what most uploads look like.</p></div>
        </>
      )}
    </>
  );
}
