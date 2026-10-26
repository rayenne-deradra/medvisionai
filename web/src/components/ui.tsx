// Building blocks of the Pulse design system.
import { useRef, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import { UploadCloud } from "lucide-react";
import { pct, type Sample } from "../api";

/** The heartbeat line from the logo: brand motif for empty and loading states. */
export function PulseLine({ className = "pulse-line" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 160 40" fill="none" aria-hidden>
      <path d="M2 22 H46 L56 6 L70 36 L80 16 L88 22 H158" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function PageHead({ icon, eyebrow, title, children, aside }: { icon?: ReactNode; eyebrow: string; title: string; children?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="page-head">
      <div>
        <div className="eyebrow">{icon}{eyebrow}</div>
        <h1 className="h1">{title}</h1>
        {children && <p className="lead">{children}</p>}
      </div>
      {aside}
    </header>
  );
}

export function SectionHead({ title, note }: { title: string; note?: string }) {
  return <div className="section-head"><h2 className="h2">{title}</h2>{note && <p>{note}</p>}</div>;
}

export function Dropzone({ onFile, hint, disabled }: { onFile: (f: File) => void; hint: string; disabled?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const open = () => !disabled && input.current?.click();
  return (
    <div className={`drop${over ? " over" : ""}`} role="button" tabIndex={0} aria-disabled={disabled} onClick={open}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && open()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f && !disabled) onFile(f); }}>
      <div className="ic"><UploadCloud size={22} /></div>
      <b>Drop an image or browse</b>
      <span>{hint}</span>
      <input ref={input} type="file" hidden accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
    </div>
  );
}

export function SampleGrid({ samples, onPick, color, busy }: { samples: Sample[]; onPick: (s: Sample) => void; color: (s: Sample) => string; busy?: boolean }) {
  return (
    <div className="samples">
      {samples.map((s) => (
        <button key={s.name} className="sample" onClick={() => onPick(s)} disabled={busy} title={`Analyse this sample (true label: ${s.truth})`}>
          <div className="thumb"><img src={s.url} alt="" loading="lazy" /><i style={{ ["--c" as string]: color(s) }} /></div>
          <b>{s.label}</b><span>{s.tag}</span>
        </button>
      ))}
    </div>
  );
}

export function Seg<T extends string>({ value, options, onChange, label }: { value: T; options: [T, string][]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="seg" role="radiogroup" aria-label={label}>
      {options.map(([v, text]) => (
        <button key={v} type="button" role="radio" aria-checked={v === value} className={v === value ? "on" : ""} onClick={() => onChange(v)}>{text}</button>
      ))}
    </div>
  );
}

export function Slider({ label, value, min, max, step, onChange, format }: { label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; format: (v: number) => string }) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className="slider"><input type="range" min={min} max={max} step={step} value={value} aria-label={label}
        onChange={(e) => onChange(Number(e.target.value))} /><output>{format(value)}</output></div>
    </div>
  );
}

export function Switch({ label, help, checked, onChange }: { label: string; help?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="switch"><span>{label}{help && <small>{help}</small>}</span>
      <input type="checkbox" role="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} /></label>
  );
}

export function Bars({ probs, top, hot }: { probs: Record<string, number>; top: string; hot?: string }) {
  return (
    <div className="bars">
      {Object.entries(probs).sort((a, b) => b[1] - a[1]).map(([name, p], i) => (
        <div key={name} className={`bar ${name === hot ? "hot" : name === top ? "top" : ""}`}>
          <span className="n">{name}</span>
          <span className="track"><span className="fill" style={{ width: `${Math.max(p, 0.004) * 100}%`, animationDelay: `${i * 0.05}s` }} /></span>
          <span className="p">{pct(p)}</span>
        </div>
      ))}
    </div>
  );
}

/** Semicircular 0–100 gauge for the triage risk score. */
export function Dial({ value, level }: { value: number; level: "low" | "medium" | "high" }) {
  const color = level === "high" ? "var(--danger)" : level === "medium" ? "var(--warning)" : "var(--success)";
  const arc = Math.PI * 60;
  return (
    <div className="dial">
      <svg viewBox="0 0 140 84" role="img" aria-label={`Triage risk score ${Math.round(value)} out of 100, ${level}`}>
        <path d="M10 76 A60 60 0 0 1 130 76" fill="none" stroke="var(--navy-50)" strokeWidth="12" strokeLinecap="round" />
        <motion.path d="M10 76 A60 60 0 0 1 130 76" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={arc} initial={{ strokeDashoffset: arc }} animate={{ strokeDashoffset: arc * (1 - value / 100) }}
          transition={{ duration: 1.1, ease: [0.2, 0.7, 0.2, 1] }} />
        <text x="70" y="66" textAnchor="middle" className="val">{Math.round(value)}</text>
        <text x="70" y="82" textAnchor="middle" className="cap">triage score / 100</text>
      </svg>
      <div className="lvl" style={{ color }}>{level === "high" ? "Urgent review" : level === "medium" ? "Specialist review" : "Routine review"}</div>
    </div>
  );
}

export function Verdict({ tone, kicker, title, sub, badge, side, facts }: { tone: "danger" | "success" | "neutral"; kicker: ReactNode; title: string; sub: string;
  badge?: ReactNode; side?: ReactNode; facts?: [string, ReactNode][] }) {
  return (
    <motion.section className="card" style={{ padding: 0, overflow: "hidden" }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className={`verdict ${tone}`}>
        <div><div className="kicker">{kicker}{badge}</div><h2>{title}</h2><div className="sub">{sub}</div></div>
        {side}
      </div>
      {facts && <dl className="facts">{facts.map(([k, v]) => <div key={k} className="fact"><dt>{k}</dt><dd>{v}</dd></div>)}</dl>}
    </motion.section>
  );
}

export function Empty({ title, children, loading }: { title: string; children: ReactNode; loading?: boolean }) {
  return (
    <div className={`card empty${loading ? " loading" : ""}`} aria-live="polite">
      <PulseLine />
      <div className="h3">{title}</div>
      <p>{children}</p>
    </div>
  );
}

export function downloadJson(data: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}
