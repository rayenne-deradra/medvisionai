import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Brain, CalendarClock, CheckCircle2, Download, Images, Info, MessageSquareText, RefreshCw, SlidersHorizontal } from "lucide-react";
import { api, pct, type Case, type Report, type Sample } from "../api";
import { useStore } from "../store";
import { Bars, Dial, downloadJson, Dropzone, Empty, PageHead, SampleGrid, Seg, Slider, Switch, Verdict } from "../components/ui";

const VIEWS: [string, string][] = [["overlay", "Lesion outline"], ["probability", "Lesion heatmap"], ["saliency", "CNN saliency"], ["mask", "Binary mask"]];
const COLORS: Record<string, string> = { glioma: "#D9822B", meningioma: "#5562C4", pituitary: "#0F7D68" };
const NAMES: Record<string, string> = { glioma: "Glioma", meningioma: "Meningioma", pituitary: "Pituitary tumour", no_tumor: "No tumour" };

export default function BrainMRI() {
  const { cases, addCase, setPendingCase, requireAuth } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [current, setCurrent] = useState<Case | null>(() => cases.find((c) => c.modality === "brain_mri") || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState("overlay");
  const [opts, setOpts] = useState({ plane: "auto", threshold: 0.35, tta: true, force: false });
  const started = useRef(false);
  const last = useRef<{ file?: File; sample?: string } | null>(null);

  const run = (input: { file?: File; sample?: string }) => requireAuth(async () => {
    last.current = input;
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
  }, "Analysing an MRI slice needs your organisation's activation code.");

  useEffect(() => {
    api.get<{ brain: Sample[] }>("/api/samples").then((s) => setSamples(s.brain)).catch(() => {});
    const sample = (location.state as { sample?: string } | null)?.sample;
    if (sample && !started.current) { started.current = true; run({ sample }); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const r = current?.report;
  const assessed = !!r?.risk;
  const tumour = assessed && r.predicted_class !== "No tumour";
  return (
    <>
      <PageHead icon={<Brain size={16} />} eyebrow="Neuro-oncology · BRISC 2025" title="Brain tumour MRI">
        Upload a T1-weighted brain MRI slice. Four CNNs classify it, a U-Net outlines the lesion, and a triage score suggests how soon a specialist should review it.
      </PageHead>

      <div className="workbench">
        <aside className="stack">
          <div className="card">
            <div className="card-head"><h2 className="h3"><SlidersHorizontal size={18} />Slice settings</h2></div>
            <p className="hint" style={{ marginTop: 0 }}>The platform picks the model: the validated 5-fold EfficientNet-B0 ensemble, checked against three other CNNs.</p>
            <div className="field"><span className="field-label">Anatomical plane</span>
              <Seg label="Anatomical plane" value={opts.plane} onChange={(plane) => setOpts({ ...opts, plane })}
                options={[["auto", "Auto"], ["axial", "Axial"], ["coronal", "Coronal"], ["sagittal", "Sagittal"]]} />
              <div className="hint">Auto reads the plane from the file name; pick it yourself when the name doesn't say.</div></div>
            <Slider label="Lesion threshold" value={opts.threshold} min={0.15} max={0.75} step={0.05} format={(v) => v.toFixed(2)}
              onChange={(threshold) => setOpts({ ...opts, threshold })} />
            <Switch label="Mirror augmentation" help="Averages each CNN over the image and its mirror." checked={opts.tta} onChange={(tta) => setOpts({ ...opts, tta })} />
            <Switch label="Allow non-MRI images" help="Runs the models on colour images too (unreliable)." checked={opts.force} onChange={(force) => setOpts({ ...opts, force })} />
            {last.current && !busy && (
              <button className="btn primary" style={{ marginTop: 14, width: "100%" }} onClick={() => last.current && run(last.current)}>
                <RefreshCw size={16} />Re-run this slice with these settings</button>)}
          </div>
          <div className="card">
            <div className="card-head"><h2 className="h3"><Images size={18} />Image</h2></div>
            <Dropzone onFile={(file) => run({ file })} hint="JPEG, PNG, TIFF, BMP or WebP · up to 10 MB" disabled={busy} />
            <div className="field-label" style={{ marginTop: 18 }}>Or try a test slice</div>
            <SampleGrid samples={samples} busy={busy} onPick={(s) => run({ sample: s.name })} color={(s) => COLORS[s.truth.split(" ")[0]] || "#9AA0B8"} />
          </div>
        </aside>

        <section className="stack" aria-live="polite">
          {error && <div className="alert danger"><AlertCircle size={18} />{error}</div>}
          {busy ? (
            <Empty title="Reading the slice" loading>Four CNNs, a U-Net and the radiomics models are running. The first analysis after a pause also loads the models (up to a minute).</Empty>
          ) : !r || !current ? (
            <Empty title="No analysis yet">Upload a slice or pick a test slice on the left. You'll see the predicted class, the lesion outline, how certain the models are, and a triage score.</Empty>
          ) : (
            <motion.div key={current.id} className="stack" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Verdict tone={!assessed ? "neutral" : tumour ? "danger" : "success"}
                kicker={<>{tumour ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}Finding</>}
                badge={<span className={`badge ${r.confidence.split(" ")[0]}`} style={{ marginLeft: 6 }}>{r.confidence} confidence</span>}
                title={r.finding} sub={assessed ? `${r.filename} · ${r.plane} plane · ${r.selected_model}` : r.filename}
                side={assessed ? <Dial value={r.risk.score} level={r.risk.level} /> : undefined}
                facts={assessed ? [["Predicted class", r.predicted_class], ["Model certainty", pct(r.predicted_probability)],
                  ["Lesion area", `${r.segmentation.lesion_area_percent.toFixed(2)}% · ${r.segmentation.lesion_size}`],
                  ["CNN agreement", `${Object.values(r.backbones as Record<string, Report>).filter((b) => NAMES[b.predicted_class] === r.predicted_class).length} of ${Object.keys(r.backbones).length}`]]
                  : [["Image check", r.input_check.image_type]]} />

              <div className="viewer">
                {assessed && <div className="tabs-dark" role="tablist">{VIEWS.map(([v, l]) => (
                  <button key={v} role="tab" aria-selected={view === v} className={view === v ? "on" : ""} onClick={() => setView(v)}>{l}</button>))}</div>}
                <div className="pair">
                  <figure><img src={current.images.original} alt="MRI slice" /><figcaption>Original</figcaption></figure>
                  {assessed && <AnimatePresence mode="wait"><motion.figure key={view} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
                    <img src={current.images[view]} alt={VIEWS.find(([v]) => v === view)?.[1]} /><figcaption>{VIEWS.find(([v]) => v === view)?.[1]}</figcaption></motion.figure></AnimatePresence>}
                </div>
                <p className="legend">{assessed ? "Blue fill with a gold outline marks the U-Net lesion. Heatmaps go from dark (little) to bright (strong). They show where the models looked, not proof of disease."
                  : "The models did not assess this image."}</p>
              </div>

              {assessed && (
                <div className="grid-2">
                  <div className="card"><div className="card-head"><h3 className="h3">Class probabilities</h3><span className="xs muted">{r.selected_model}</span></div>
                    <Bars probs={r.class_probabilities} top={r.predicted_class} hot={tumour ? r.predicted_class : undefined} /></div>
                  {r.segmentation.centroid ? (
                    <div className="card"><div className="card-head"><h3 className="h3">Lesion shape</h3><span className="xs muted">U-Net</span></div>
                      <dl className="kv">
                        <div><dt>Bounding box</dt><dd>{r.segmentation.bbox_area_px.toLocaleString()} px²</dd></div>
                        <div><dt>Compactness</dt><dd>{r.segmentation.compactness.toFixed(3)}</dd></div>
                        <div><dt>Intensity contrast</dt><dd>{r.segmentation.intensity_contrast.toFixed(1)}</dd></div>
                        <div><dt>Centre (x, y)</dt><dd>{Math.round(r.segmentation.centroid[0])}, {Math.round(r.segmentation.centroid[1])}</dd></div>
                      </dl><p className="hint">Compactness 1.0 is a perfect circle; lower means a more irregular outline.</p></div>
                  ) : <div className="card"><h3 className="h3">Lesion shape</h3><p className="small muted">The U-Net found no lesion above the threshold.</p></div>}
                  <div className="card"><div className="card-head"><h3 className="h3">Model agreement</h3>{r.tta && <span className="xs muted">with mirror augmentation</span>}</div>
                    <table className="tbl"><thead><tr><th>Model</th><th>Prediction</th><th className="num">Probability</th></tr></thead><tbody>
                      {Object.values(r.backbones as Record<string, Report>).map((b) => (
                        <tr key={b.title} className={b.title === r.selected_model ? "sel" : ""}><td>{b.title}</td><td>{NAMES[b.predicted_class] || b.predicted_class}</td>
                          <td className="num">{pct(b.probability)}</td></tr>))}</tbody></table></div>
                  {r.classical?.length > 0 && <div className="card"><div className="card-head"><h3 className="h3">Second opinion</h3><span className="xs muted">classical radiomics</span></div>
                    <table className="tbl"><thead><tr><th>Model</th><th>Vote</th><th className="num">P(tumour)</th></tr></thead><tbody>
                      {r.classical.map((c: Report) => <tr key={c.model}><td>{c.model}</td><td><span className={`badge ${c.label === "tumour" ? "danger" : "success"}`}>{c.label}</span></td>
                        <td className="num">{pct(c.tumor_probability)}</td></tr>)}</tbody></table>
                    <p className="hint">Seven image-level features; weaker evidence than the CNNs.</p></div>}
                </div>
              )}

              <div className="card"><div className="card-head"><h3 className="h3"><Info size={18} />Why this confidence</h3></div>
                <ul className="checks">{r.confidence_reasons.map((x: string, i: number) => <li key={i}><CheckCircle2 size={16} />{x}</li>)}</ul>
                {assessed && <div className="alert info" style={{ marginTop: 16 }}><Info size={18} /><span><b>{r.risk.priority}.</b> {r.risk.explanation}</span></div>}
                <p className="hint">{r.model.backbone} · {r.created_utc} · Research use only, not a diagnosis.</p></div>

              <div className="actions">
                <button className="btn primary" onClick={() => { setPendingCase(current.id); navigate("/assistant"); }}><MessageSquareText size={17} />Discuss with the assistant</button>
                {assessed && <button className="btn" onClick={() => navigate("/appointments", { state: { caseId: current.id, specialist: r.risk.level === "high" ? "neuro-oncology" : "neuroradiology" } })}>
                  <CalendarClock size={17} />Refer to a specialist</button>}
                <button className="btn quiet" onClick={() => downloadJson(r, "medvision_brain_report.json")}><Download size={17} />Download report</button>
              </div>
            </motion.div>
          )}
        </section>
      </div>
    </>
  );
}
