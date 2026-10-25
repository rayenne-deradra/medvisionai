import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, pct, type Case, type Report, type Sample } from "../api";
import { useStore } from "../store";
import { Dropzone, downloadJson, Finding, Kpi, PageHead, Probs, Reasons, Reveal, Ruler, SampleGrid, Scanning, Section, Seg } from "../components/ui";

const TUMOUR = "Colorectal adenocarcinoma epithelium";

export default function Colorectal() {
  const { cases, addCase, setPendingCase } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [current, setCurrent] = useState<Case | null>(() => cases.find((c) => c.modality === "colorectal") || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [opts, setOpts] = useState({ mode: "Auto", tile_size: "Auto", min_tumor_fraction: 0.1, alpha: 0.5, force: false });
  const started = useRef(false);

  async function run(input: { file?: File; sample?: string }) {
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
  }

  useEffect(() => {
    api.get<{ colorectal: Sample[] }>("/api/samples").then((s) => setSamples(s.colorectal)).catch(() => {});
    const sample = (location.state as { sample?: string } | null)?.sample;
    if (sample && !started.current) { started.current = true; run({ sample }); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const r = current?.report;
  const assessed = !!r?.predicted_class;
  const tone = r?.finding === "Tumour tissue detected" ? "rose" : r?.finding === "No tumour tissue detected" ? "teal" : "muted";
  return (
    <>
      <PageHead kicker="Histopathology · NCT-CRC-HE-100K" title="Colorectal tissue">
        Upload an H&amp;E image of colon or rectum tissue. The Phikon foundation model classifies it into 9 tissue types with calibrated
        confidence, flags tumour tissue and shows a Grad-CAM map. Large images are read tile by tile.
      </PageHead>

      <Section title="Analyse an image" note="H&E · ideally 224 × 224 px at ~20×" />
      <Dropzone onFile={(file) => run({ file })} hint="PNG, JPEG, TIFF, BMP or WebP, up to 10 MB. Large images are scanned tile by tile." />
      <details className="settings">
        <summary>Analysis settings</summary>
        <div className="body">
          <div className="field"><span>Mode</span>
            <Seg value={opts.mode} onChange={(mode) => setOpts({ ...opts, mode })} options={[["Auto", "Auto"], ["Single patch", "Single patch"], ["Tile scan", "Tile scan"]]} /></div>
          <label className="field"><span>Tile size</span>
            <select className="input" value={opts.tile_size} onChange={(e) => setOpts({ ...opts, tile_size: e.target.value })}>
              {["Auto", "224", "320", "448", "672", "896"].map((t) => <option key={t} value={t}>{t === "Auto" ? "Auto (at most 4 × 4)" : `${t} px`}</option>)}
            </select></label>
          <label className="field"><span>Tumour tiles needed · {Math.round(opts.min_tumor_fraction * 100)}%</span>
            <input className="range" type="range" min={0.05} max={0.5} step={0.05} value={opts.min_tumor_fraction}
              onChange={(e) => setOpts({ ...opts, min_tumor_fraction: Number(e.target.value) })} /></label>
          <label className="field"><span>Heatmap opacity · {opts.alpha.toFixed(2)}</span>
            <input className="range" type="range" min={0.2} max={0.8} step={0.05} value={opts.alpha}
              onChange={(e) => setOpts({ ...opts, alpha: Number(e.target.value) })} /></label>
          <label className="toggle"><input type="checkbox" checked={opts.force} onChange={(e) => setOpts({ ...opts, force: e.target.checked })} />Analyse out-of-scope images anyway</label>
        </div>
      </details>

      <AnimatePresence>
        {busy && <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} style={{ marginTop: 16 }}>
          <Scanning title="Reading the tissue…" text="Checking the stain, classifying and computing Grad-CAM. The first analysis loads the pathology model." />
        </motion.div>}
      </AnimatePresence>
      {error && <div className="alert error" style={{ marginTop: 16 }}>{error}</div>}

      {r && current && (
        <motion.div key={current.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <Section title="Result" note="calibrated 9-class tissue classification" />
          <div className="result">
            <Finding title={r.finding} confidence={r.confidence} tone={tone} sub={`${r.filename} · ${r.analysis_mode}`} />
            <div className="kpis">
              {assessed && <Kpi k={`Tumour probability${r.tiles ? " · max tile" : ""}`}><div className="v big">{pct(r.tumor_probability)}</div><Ruler value={r.tumor_probability} /></Kpi>}
              {assessed && <Kpi k={r.tiles ? "Dominant tissue" : "Predicted tissue"}><div className="v">{r.predicted_class}</div></Kpi>}
              {assessed && (r.tiles ? <Kpi k="Tumour tiles"><div className="v">{r.tiles.n_tumor_tiles} of {r.tiles.n_tissue_tiles}</div></Kpi>
                : <Kpi k="Model certainty"><div className="v">{pct(r.predicted_probability)}</div></Kpi>)}
              <Kpi k="Image check"><div className="v">{r.input_check.image_type}</div></Kpi>
            </div>
          </div>
          <div className="grid2">
            <div className="stack">
              <div className="card">
                <h3 style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: "1.25rem", margin: "0 0 14px" }}>Tissue &amp; Grad-CAM</h3>
                <div className="plates">
                  <div><div className="plate-cap">Original</div><div className="plate"><img src={current.images.original} alt="H&E image" /></div></div>
                  {current.images.overlay ? <div><div className="plate-cap">Grad-CAM overlay</div><div className="plate"><img src={current.images.overlay} alt="Grad-CAM overlay" /></div></div>
                    : <div className="alert info">No heatmap: the classifier did not assess this image.</div>}
                </div>
                {current.images.overlay && <div className="foot">Untinted = little influence; red to yellow = strongest evidence for “{r.heatmap_target}”.</div>}
              </div>
              <div className="card"><div className="label">Why this confidence</div><Reasons items={r.confidence_reasons} />
                {r.tiles && <div className="foot">{r.tiles.rule}</div>}
                <div className="foot">{r.model.backbone} · {r.created_utc} · Research use only, not a diagnosis.</div></div>
            </div>
            {assessed && <Reveal className="card"><div className="label">{r.tiles ? "Tissue composition (mean over tiles)" : "Confidence scores (calibrated)"}</div>
              <Probs probs={r.class_probabilities} top={r.predicted_class} tumour={TUMOUR} /></Reveal>}
          </div>
          <div className="actions">
            <button className="btn primary" onClick={() => { setPendingCase(current.id); navigate("/assistant"); }}>Discuss with the AI Assistant</button>
            {assessed && <button className="btn" onClick={() => navigate("/appointments", { state: { caseId: current.id, specialist: "gi-pathology" } })}>Refer to a specialist</button>}
            <button className="btn" onClick={() => downloadJson(r, "medvision_tissue_report.json")}>Download report</button>
          </div>
        </motion.div>
      )}

      <Section title={current ? "Try another sample" : "Or try a sample"} note="CRC-VAL-HE-7K test patches · true label on hover" />
      <SampleGrid samples={samples} onPick={(s) => !busy && run({ sample: s.name })}
        ring={(s) => (s.truth.includes("adenocarcinoma") || s.tag === "tile scan" ? "#E8B5C9" : "#E2E5EE")} />
    </>
  );
}
