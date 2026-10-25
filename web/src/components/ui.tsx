// Small building blocks shared by the pages.
import { useRef, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import { pct, type Sample } from "../api";

export function PageHead({ kicker, title, children }: { kicker: string; title: string; children?: ReactNode }) {
  return (
    <header className="head">
      <span className="kicker">{kicker}</span>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}

export function Section({ title, note }: { title: string; note?: string }) {
  return <div className="sec"><h2>{title}</h2>{note && <span>{note}</span>}</div>;
}

/** Fades and lifts its children into view, one after another. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }} transition={{ duration: 0.6, delay, ease: [0.2, 0.7, 0.2, 1] }}>
      {children}
    </motion.div>
  );
}

export function Dropzone({ onFile, hint }: { onFile: (f: File) => void; hint: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <div className={`drop${over ? " over" : ""}`} role="button" tabIndex={0} onClick={() => input.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}>
      <div className="ic">↑</div>
      <div><b>Drop an image here, or click to upload</b><span>{hint}</span></div>
      <input ref={input} type="file" hidden accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
    </div>
  );
}

export function SampleGrid({ samples, onPick, ring }: { samples: Sample[]; onPick: (s: Sample) => void; ring: (s: Sample) => string }) {
  return (
    <div className="samples">
      {samples.map((s, i) => (
        <motion.button key={s.name} className="sample" onClick={() => onPick(s)} title={`True label: ${s.truth}`}
          style={{ ["--ring" as string]: ring(s) }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.03 * i, duration: 0.4 }}>
          <img src={s.url} alt="" loading="lazy" />
          <div><b>{s.label}</b><span>{s.tag}</span></div>
        </motion.button>
      ))}
    </div>
  );
}

export function Seg<T extends string>({ value, options, onChange }: { value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return (
    <div className="seg" role="radiogroup">
      {options.map(([v, label]) => (
        <button key={v} type="button" role="radio" aria-checked={v === value} className={v === value ? "on" : ""} onClick={() => onChange(v)}>{label}</button>
      ))}
    </div>
  );
}

export function Scanning({ title, text }: { title: string; text: string }) {
  return (
    <div className="card scanning" aria-live="polite">
      <div className="mini" />
      <div><b>{title}</b><div className="small muted">{text}</div></div>
    </div>
  );
}

export function Kpi({ k, children }: { k: string; children: ReactNode }) {
  return <div className="kpi"><div className="k">{k}</div>{children}</div>;
}

export function Ruler({ value, risk }: { value: number; risk?: boolean }) {
  return <div className={`ruler${risk ? " risk" : ""}`}><span style={{ width: `${Math.max(value, 0.01) * 100}%` }} /></div>;
}

export function Probs({ probs, top, tumour }: { probs: Record<string, number>; top: string; tumour?: string }) {
  return (
    <>
      {Object.entries(probs).sort((a, b) => b[1] - a[1]).map(([name, p]) => (
        <div key={name} className={`prob ${name === tumour ? "tumor" : name === top ? "top" : ""}`}>
          <span className="n">{name}</span>
          <span className="track"><span className="fill" style={{ width: `${Math.max(p, 0.004) * 100}%` }} /></span>
          <span className="p">{pct(p)}</span>
        </div>
      ))}
    </>
  );
}

export function Reasons({ items }: { items: string[] }) {
  return <ul className="reasons">{items.map((r, i) => <li key={i}>{r}</li>)}</ul>;
}

export function Finding({ title, sub, tone, confidence }: { title: string; sub: string; tone: "rose" | "teal" | "muted"; confidence: string }) {
  return (
    <div className="result-top">
      <div className={`finding ${tone}`}>
        <div className="ic">{tone === "rose" ? "!" : tone === "teal" ? "✓" : "–"}</div>
        <div><div className="t">{title}</div><div className="s">{sub}</div></div>
      </div>
      <span className={`chip ${confidence.split(" ")[0]}`}>Confidence: {confidence}</span>
    </div>
  );
}

export function downloadJson(data: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}
