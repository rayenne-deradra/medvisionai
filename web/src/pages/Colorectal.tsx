import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertCircle, CalendarClock, CheckCircle2, Download, Images, Info, MessageSquareText, Microscope, SlidersHorizontal } from "lucide-react";
import { api, pct, type Case, type Report, type Sample } from "../api";
import { useStore } from "../store";
import { Bars, downloadJson, Dropzone, Empty, PageHead, SampleGrid, Seg, Slider, Switch, Verdict } from "../components/ui";

const TUMOUR = "Colorectal adenocarcinoma epithelium";

export default function Colorectal() {
  const { cases, addCase, setPendingCase, requireAuth } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [current, setCurrent] = useState<Case | null>(() => cases.find((c) => c.modality === "colorectal") || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [opts, setOpts] = useState({ mode: "Auto", tile_size: "Auto", min_tumor_fraction: 0.1, alpha: 0.5, force: false });
  const started = useRef(false);

  const run = (input: { file?: File; sample?: string }) => requireAuth(async () => {
    setBusy(true); setError("");
    const form = new FormData();
    if (input.file) form.append("file", input.file);
    if (input.sample) form.append("sample", input.sample);
    form.append("mode", opts.mode);
    if (opts.tile_size !== "Auto") form.append("tile_size", opts.tile_size);
    form.append("min_tumor_fraction", String(opts.min_tumor_fraction));
    form.append("alpha", String(opts.alpha));
    form.append("force", String(opts.force));
    try {
      const r = await api.form<{ case_id: string; report: Report; images: Record<string, string> }>("/api/analyze/colorectal", form);
      const c: Case = { id: r.case_id, modality: "colorectal", report: r.report, images: r.images };
      addCase(c); setCurrent(c);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, "Analysing tissue needs your organisation's activation code.");

  useEffect(() => {
    api.get<{ colorectal: Sample[] }>("/api/samples").then((s) => setSamples(s.colorectal)).catch(() => {});
    const sample = (location.state as { sample?: string } | null)?.sample;
    if (sample && !started.current) { started.current = true; run({ sample }); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const r = current?.report;
  const assessed = !!r?.predicted_class;
  const tumour = r?.finding === "Tumour tissue detected";
  return (
    <>
      <PageHead icon={<Microscope size={16} />} eyebrow="Histopathology · NCT-CRC-HE-100K" title="Colorectal tissue">
        Upload an H&amp;E image of colon or rectum tissue. The Phikon foundation model classifies it into nine tissue types with calibrated confidence and shows which regions drove the result.
      </PageHead>

      <div className="workbench">
        <aside className="stack">
          <div className="card">
            <div className="card-head"><h2 className="h3"><Images size={18} />Image</h2></div>
            <Dropzone onFile={(file) => run({ file })} hint="H&E · ideally 224 × 224 px at about 20× · up to 10 MB" disabled={busy} />
            <div className="field-label" style={{ marginTop: 18 }}>Or try a test patch</div>
            <SampleGrid samples={samples} busy={busy} onPick={(s) => run({ sample: s.name })}
              color={(s) => (s.truth.includes("adenocarcinoma") || s.tag === "tile scan" ? "#C2364A" : "#9AA0B8")} />
          </div>
          <div className="card">
            <div className="card-head"><h2 className="h3"><SlidersHorizontal size={18} />Settings</h2></div>
            <div className="field"><span className="field-label">Analysis mode</span>
              <Seg label="Analysis mode" value={opts.mode} onChange={(mode) => setOpts({ ...opts, mode })}
                options={[["Auto", "Auto"], ["Single patch", "One patch"], ["Tile scan", "Tile scan"]]} />
              <div className="hint">Auto reads images up to 336 px as one patch and scans larger ones tile by tile.</div></div>
            <div className="field"><label className="field-label" htmlFor="tile">Tile size</label>
              <select id="tile" className="input" value={opts.tile_size} onChange={(e) => setOpts({ ...opts, tile_size: e.target.value })}>
                {["Auto", "224", "320", "448", "672", "896"].map((t) => <option key={t} value={t}>{t === "Auto" ? "Automatic (at most 4 × 4)" : `${t} px`}</option>)}</select></div>
            <Slider label="Tumour tiles needed to flag" value={opts.min_tumor_fraction} min={0.05} max={0.5} step={0.05}
              format={(v) => `${Math.round(v * 100)}%`} onChange={(v) => setOpts({ ...opts, min_tumor_fraction: v })} />
            <Slider label="Heatmap opacity" value={opts.alpha} min={0.2} max={0.8} step={0.05} format={(v) => v.toFixed(2)} onChange={(alpha) => setOpts({ ...opts, alpha })} />
            <Switch label="Allow non-H&E images" help="Runs the model on any image (unreliable)." checked={opts.force} onChange={(force) => setOpts({ ...opts, force })} />
          </div>
        </aside>

        <section className="stack" aria-live="polite">
          {error && <div className="alert danger"><AlertCircle size={18} />{error}</div>}
          {busy ? (
            <Empty title="Reading the tissue" loading>Checking the stain, classifying and computing the heatmap. The first analysis after a pause also loads the model.</Empty>
          ) : !r || !current ? (
            <Empty title="No analysis yet">Upload an H&amp;E image or pick a test patch on the left. You'll see the tissue type, whether tumour tissue was found, and where the model looked.</Empty>
          ) : (
            <motion.div key={current.id} className="stack" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Verdict tone={!assessed ? "neutral" : tumour ? "danger" : "success"}
                kicker={<>{tumour ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}Finding</>}
                badge={<span className={`badge ${r.confidence.split(" ")[0]}`} style={{ marginLeft: 6 }}>{r.confidence} confidence</span>}
                title={r.finding} sub={`${r.filename} · ${r.analysis_mode}`}
                facts={assessed ? [
                  [`Tumour probability${r.tiles ? " (max tile)" : ""}`, <>{pct(r.tumor_probability)}<div className="meter"><span style={{ width: `${Math.max(r.tumor_probability, 0.01) * 100}%` }} /></div></>],
                  [r.tiles ? "Dominant tissue" : "Predicted tissue", r.predicted_class],
                  r.tiles ? ["Tumour tiles", `${r.tiles.n_tumor_tiles} of ${r.tiles.n_tissue_tiles}`] : ["Model certainty", pct(r.predicted_probability)],
                  ["Image check", r.input_check.image_type]] : [["Image check", r.input_check.image_type]]} />

              <div className="viewer">
                <div className="pair">
                  <figure><img src={current.images.original} alt="H&E image" /><figcaption>Original</figcaption></figure>
                  {current.images.overlay && <figure><img src={current.images.overlay} alt="Grad-CAM overlay" /><figcaption>Grad-CAM</figcaption></figure>}
                </div>
                <p className="legend">{current.images.overlay ? `Untinted areas had little influence; red to yellow marks the strongest evidence for "${r.heatmap_target}".`
                  : "No heatmap: the classifier did not assess this image."}</p>
              </div>

              <div className="grid-2">
                {assessed && <div className="card"><div className="card-head"><h3 className="h3">{r.tiles ? "Tissue composition" : "Confidence by tissue type"}</h3>
                  <span className="xs muted">{r.tiles ? "mean over tiles" : "calibrated"}</span></div>
                  <Bars probs={r.class_probabilities} top={r.predicted_class} hot={TUMOUR} /></div>}
                <div className="card"><div className="card-head"><h3 className="h3"><Info size={18} />Why this confidence</h3></div>
                  <ul className="checks">{r.confidence_reasons.map((x: string, i: number) => <li key={i}><CheckCircle2 size={16} />{x}</li>)}</ul>
                  {r.tiles && <p className="hint">{r.tiles.rule}</p>}
                  <p className="hint">{r.model.backbone} · {r.created_utc} · Research use only, not a diagnosis.</p></div>
              </div>

              <div className="actions">
                <button className="btn primary" onClick={() => { setPendingCase(current.id); navigate("/assistant"); }}><MessageSquareText size={17} />Discuss with the assistant</button>
                {assessed && <button className="btn" onClick={() => navigate("/appointments", { state: { caseId: current.id, specialist: "gi-pathology" } })}>
                  <CalendarClock size={17} />Refer to a specialist</button>}
                <button className="btn quiet" onClick={() => downloadJson(r, "medvision_tissue_report.json")}><Download size={17} />Download report</button>
              </div>
            </motion.div>
          )}
        </section>
      </div>
    </>
  );
}
