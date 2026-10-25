import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, pct, type Case, type Report, type Sample } from "../api";
import { useStore } from "../store";
import { Dropzone, downloadJson, Finding, Kpi, PageHead, Probs, Reasons, Reveal, Ruler, SampleGrid, Scanning, Section, Seg } from "../components/ui";

const VIEWS: [string, string][] = [["overlay", "Contour"], ["probability", "Heatmap"], ["saliency", "Saliency"], ["mask", "Mask"]];
const VIEW_TITLE: Record<string, string> = { overlay: "U-Net lesion contour", probability: "U-Net probability heatmap", saliency: "CNN saliency map", mask: "Binary lesion mask" };
const RING: Record<string, string> = { glioma: "#F2C9A1", meningioma: "#C9CFF0", pituitary: "#C7E4D8" };
const MODELS: [string, string][] = [["ensemble", "EfficientNet-B0 · 5-fold ensemble"], ["efficientnet_b0", "EfficientNet-B0 · single"],
  ["convnext_tiny", "ConvNeXt-Tiny"], ["resnet18", "ResNet-18"]];
const NAMES: Record<string, string> = { glioma: "Glioma", meningioma: "Meningioma", pituitary: "Pituitary tumour", no_tumor: "No tumour" };

export default function BrainMRI() {
  const { cases, addCase, setPendingCase } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [current, setCurrent] = useState<Case | null>(() => cases.find((c) => c.modality === "brain_mri") || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState("overlay");
  const [opts, setOpts] = useState({ backbone: "ensemble", plane: "auto", threshold: 0.35, tta: true, force: false });
  const started = useRef(false);

  async function run(input: { file?: File; sample?: string }) {
    setBusy(true); setError("");
    const form = new FormData();
    if (input.file) form.append("file", input.file);
    if (input.sample) form.append("sample", input.sample);
    Object.entries(opts).forEach(([k, v]) => form.append(k, String(v)));
    try {
      const r = await api.form<{ case_id: string; report: Report; images: Record<string, string> }>("/api/analyze/brain", form);
      const c: Case = { id: r.case_id, modality: "brain_mri", report: r.report, images: r.images };
      addCase(c); setCurrent(c); setView("overlay");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    api.get<{ brain: Sample[] }>("/api/samples").then((s) => setSamples(s.brain)).catch(() => {});
    const sample = (location.state as { sample?: string } | null)?.sample;
    if (sample && !started.current) { started.current = true; run({ sample }); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const r = current?.report;
  const assessed = !!r?.risk;
  return (
    <>
      <PageHead kicker="Neuro-oncology · BRISC 2025" title="Brain tumour MRI">
        Upload a T1-weighted axial, coronal or sagittal slice. Four CNNs classify it (glioma, meningioma, pituitary tumour or no tumour), a
        U-Net outlines the lesion, and a triage score suggests how soon a specialist should review it.
      </PageHead>

      <Section title="Analyse an MRI slice" note="JPEG or PNG · grayscale T1" />
      <Dropzone onFile={(file) => run({ file })} hint="PNG, JPEG, TIFF, BMP or WebP, up to 10 MB" />
      <details className="settings">
        <summary>Analysis settings</summary>
        <div className="body">
          <label className="field"><span>Reported model (all four always compared)</span>
            <select className="input" value={opts.backbone} onChange={(e) => setOpts({ ...opts, backbone: e.target.value })}>
              {MODELS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select></label>
          <div className="field"><span>Anatomical plane</span>
            <Seg value={opts.plane} onChange={(plane) => setOpts({ ...opts, plane })}
              options={[["auto", "Auto"], ["axial", "Axial"], ["coronal", "Coronal"], ["sagittal", "Sagittal"]]} /></div>
          <label className="field"><span>U-Net threshold · {opts.threshold.toFixed(2)}</span>
            <input className="range" type="range" min={0.15} max={0.75} step={0.05} value={opts.threshold}
              onChange={(e) => setOpts({ ...opts, threshold: Number(e.target.value) })} /></label>
          <div>
            <label className="toggle"><input type="checkbox" checked={opts.tta} onChange={(e) => setOpts({ ...opts, tta: e.target.checked })} />Flip test-time augmentation</label>
            <label className="toggle"><input type="checkbox" checked={opts.force} onChange={(e) => setOpts({ ...opts, force: e.target.checked })} />Analyse out-of-scope images anyway</label>
          </div>
        </div>
      </details>

      <AnimatePresence>
        {busy && <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} style={{ marginTop: 16 }}>
          <Scanning title="Reading the slice…" text="Four CNNs, a U-Net and the radiomics models. The first analysis loads the models (about 30 seconds)." />
        </motion.div>}
      </AnimatePresence>
      {error && <div className="alert error" style={{ marginTop: 16 }}>{error}</div>}

      {r && current && (
        <motion.div key={current.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <Section title="Result" note="4-class CNN ensemble · U-Net segmentation · triage score" />
          <div className="result">
            <Finding title={r.finding} confidence={r.confidence} tone={!assessed ? "muted" : r.predicted_class === "No tumour" ? "teal" : "rose"}
              sub={assessed ? `${r.filename} · ${r.plane} plane` : r.filename} />
            {assessed ? (
              <div className="kpis">
                <Kpi k="Triage risk score"><div className={`v big ${r.risk.level}`}>{Math.round(r.risk.score)}<small>/100</small></div><Ruler value={r.risk.score / 100} risk /></Kpi>
                <Kpi k="Predicted class"><div className="v">{r.predicted_class}</div></Kpi>
                <Kpi k="Model certainty"><div className="v">{pct(r.predicted_probability)}</div></Kpi>
                <Kpi k="Lesion area (U-Net)"><div className="v">{r.segmentation.lesion_area_percent.toFixed(2)}% · {r.segmentation.lesion_size}</div></Kpi>
              </div>
            ) : (
              <div className="kpis"><Kpi k="Image check"><div className="v">{r.input_check.image_type}</div></Kpi></div>
            )}
          </div>

          <div className="grid2">
            <div className="stack">
              <div className="card">
                <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
                  <h3 style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: "1.25rem", margin: 0 }}>Segmentation &amp; saliency</h3>
                  {assessed && <Seg value={view} onChange={setView} options={VIEWS} />}
                </div>
                <div className="plates">
                  <div><div className="plate-cap">Original</div><div className="plate"><img src={current.images.original} alt="MRI slice" /></div></div>
                  {assessed && <div><div className="plate-cap">{VIEW_TITLE[view]}</div>
                    <AnimatePresence mode="wait">
                      <motion.div key={view} className="plate" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
                        <img src={current.images[view]} alt={VIEW_TITLE[view]} />
                      </motion.div>
                    </AnimatePresence></div>}
                </div>
                <div className="foot">Blue fill and gold outline = U-Net lesion mask. Maps: dark = little, bright = strong. They show where the models
                  looked, not proof of disease.</div>
              </div>
              <div className="card"><div className="label">Why this confidence</div><Reasons items={r.confidence_reasons} />
                {assessed && <div className="foot"><b>{r.risk.priority}.</b> {r.risk.explanation}</div>}
                <div className="foot">{r.model.backbone} · {r.created_utc} · Research use only, not a diagnosis.</div></div>
            </div>
            {assessed && (
              <div className="stack">
                <Reveal className="card"><div className="label">Class probabilities · {r.selected_model}</div>
                  <Probs probs={r.class_probabilities} top={r.predicted_class} tumour={r.predicted_class !== "No tumour" ? r.predicted_class : undefined} /></Reveal>
                {r.segmentation.centroid && (
                  <Reveal className="card" delay={0.05}><div className="label">U-Net lesion morphology</div>
                    <div className="metrics">
                      <div><span>Bounding box</span><b>{r.segmentation.bbox_area_px.toLocaleString()} px²</b></div>
                      <div><span>Compactness</span><b>{r.segmentation.compactness.toFixed(3)}</b></div>
                      <div><span>Intensity contrast</span><b>{r.segmentation.intensity_contrast.toFixed(1)}</b></div>
                      <div><span>Centroid (x, y)</span><b>{Math.round(r.segmentation.centroid[0])}, {Math.round(r.segmentation.centroid[1])}</b></div>
                    </div><div className="foot">Compactness 1.0 = a perfect circle; lower = irregular outline.</div></Reveal>
                )}
                <Reveal className="card" delay={0.1}><div className="label">Deep-learning consensus{r.tta ? " · flip TTA" : ""}</div>
                  <table className="t"><thead><tr><th>Model</th><th>Prediction</th><th className="num">P</th></tr></thead><tbody>
                    {Object.values(r.backbones as Record<string, Report>).map((b) => (
                      <tr key={b.title} className={b.title === r.selected_model ? "sel" : ""}><td>{b.title}</td><td>{NAMES[b.predicted_class] || b.predicted_class}</td>
                        <td className="num">{pct(b.probability)}</td></tr>))}
                  </tbody></table></Reveal>
                {r.classical?.length > 0 && (
                  <Reveal className="card" delay={0.15}><div className="label">Classical radiomics · tumour vs no tumour</div>
                    <table className="t"><thead><tr><th>Model</th><th>Vote</th><th className="num">P(tumour)</th></tr></thead><tbody>
                      {r.classical.map((c: Report) => <tr key={c.model}><td>{c.model}</td>
                        <td><span className={`chip ${c.label === "tumour" ? "rose" : "teal"}`}>{c.label}</span></td><td className="num">{pct(c.tumor_probability)}</td></tr>)}
                    </tbody></table><div className="foot">Seven image-level features. Weaker evidence than the CNNs, shown as a second opinion.</div></Reveal>
                )}
              </div>
            )}
          </div>
          <div className="actions">
            <button className="btn primary" onClick={() => { setPendingCase(current.id); navigate("/assistant"); }}>Discuss with the AI Assistant</button>
            {assessed && <button className="btn" onClick={() => navigate("/appointments", { state: { caseId: current.id,
              specialist: r.risk.level === "high" ? "neuro-oncology" : "neuroradiology" } })}>Refer to a specialist</button>}
            <button className="btn" onClick={() => downloadJson(r, "medvision_brain_report.json")}>Download report</button>
          </div>
        </motion.div>
      )}

      <Section title={current ? "Try another sample" : "Or try a sample"} note="BRISC 2025 test slices · true label on hover" />
      <SampleGrid samples={samples} onPick={(s) => !busy && run({ sample: s.name })} ring={(s) => RING[s.truth.split(" ")[0]] || "#E2E5EE"} />
    </>
  );
}
