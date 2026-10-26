import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, BarChart3, Brain, CalendarClock, MessageSquareText, Microscope, Sparkles } from "lucide-react";
import { caseLabel, useStore } from "../store";
import { SectionHead } from "../components/ui";

const TOOLS = [
  { to: "/brain-mri", icon: Brain, title: "Brain tumour MRI", text: "Glioma, meningioma, pituitary tumour or no tumour from a T1 slice, with a lesion outline and a triage score." },
  { to: "/colorectal", icon: Microscope, title: "Colorectal tissue", text: "Nine tissue types from an H&E patch with calibrated confidence and a Grad-CAM map. Large slides are read tile by tile." },
  { to: "/assistant", icon: MessageSquareText, title: "AI Assistant", text: "Ask about a result or any medical imaging question. It explains and flags uncertainty, and never diagnoses." },
  { to: "/appointments", icon: CalendarClock, title: "Appointments", text: "Refer a case to neuro-oncology, neuroradiology or GI pathology. Urgent requests reach the top of the queue." },
];
const STATS = [["99.3%", "Brain MRI test accuracy (5-fold ensemble)"], ["95.1%", "Colorectal 9-class accuracy"],
  ["100%", "Colorectal tumour recall"], ["10,793", "MRI slices in the comparative study"]];
const STEPS = [["Upload or pick a sample", "A T1 MRI slice or an H&E tissue image. Real test cases are one click away."],
  ["Read the result", "Prediction, confidence and the reasons behind it, with the model's heatmap or lesion outline."],
  ["Ask the assistant", "Discuss the case in plain language: what the model saw and how certain it is."],
  ["Refer if needed", "Send an image-free summary to the right specialist with a suggested urgency."]];

export default function Platform() {
  const navigate = useNavigate();
  const { cases } = useStore();
  return (
    <>
      <section className="hero">
        <div>
          <div className="eyebrow"><Sparkles size={16} />Research prototype · radiology and pathology</div>
          <h1>Clinical Intelligence Platform for <span>medical imaging</span></h1>
          <p>Explainable AI for brain tumour MRI and colorectal histopathology: a prediction you can check, the evidence behind it,
            and a clear next step for the patient's care team.</p>
          <div className="row">
            <button className="btn primary lg" onClick={() => navigate("/brain-mri")}><Brain size={18} />Analyse a brain MRI</button>
            <button className="btn lg" onClick={() => navigate("/colorectal")}><Microscope size={18} />Analyse tissue</button>
          </div>
        </div>
        <div className="preview" aria-hidden>
          <figure><img src="/static/assets/hero_mri.jpg" alt="" /><figcaption><b>Coronal T1 slice</b>BRISC 2025 test set</figcaption></figure>
          <figure><img src="/static/assets/hero_mri_overlay.jpg" alt="" /><figcaption><b>Meningioma · 99.8%</b>U-Net lesion outline · triage 29/100</figcaption></figure>
        </div>
        <svg className="hero-pulse" viewBox="0 0 1200 60" preserveAspectRatio="none" fill="none" aria-hidden>
          <path d="M0 34 H420 L446 10 L476 56 L500 22 L516 34 H1200" stroke="currentColor" strokeWidth="2" />
        </svg>
      </section>

      <div className="stats">
        {STATS.map(([v, k]) => <div key={k} className="card stat"><b>{v}</b><span>{k}</span></div>)}
      </div>

      <SectionHead title="Tools" note="Everything is open to explore; running an analysis asks for your activation code." />
      <div className="grid-2">
        {TOOLS.map(({ to, icon: Icon, title, text }) => (
          <Link key={to} to={to} className="card tool">
            <div className="ic"><Icon size={22} /></div>
            <div><h3 className="h3" style={{ fontSize: "1.08rem" }}>{title}</h3><p style={{ marginTop: 6 }}>{text}</p></div>
            <span className="go">Open <ArrowRight size={16} /></span>
          </Link>
        ))}
      </div>

      {cases.length > 0 && (
        <>
          <SectionHead title="Recent analyses" note="This browser session only" />
          <div className="card">
            {cases.slice(0, 5).map((c) => (
              <div key={c.id} className="list-item" style={{ alignItems: "center" }}>
                <span>{caseLabel(c)}</span>
                <Link className="btn sm" to={c.modality === "brain_mri" ? "/brain-mri" : "/colorectal"}>Open</Link>
              </div>
            ))}
          </div>
        </>
      )}

      <SectionHead title="How it works" />
      <div className="steps">
        {STEPS.map(([t, d]) => <div key={t} className="card step"><h3 className="h3">{t}</h3><p>{d}</p></div>)}
      </div>

      <Link to="/benchmarks" className="card tool" style={{ marginTop: 16, flexDirection: "row", alignItems: "center" }}>
        <div className="ic"><BarChart3 size={22} /></div>
        <div style={{ flex: 1 }}><h3 className="h3">How the models were validated</h3><p>Test-set results, robustness checks and the figures behind every number above.</p></div>
        <span className="go" style={{ marginTop: 0 }}>Study & benchmarks <ArrowRight size={16} /></span>
      </Link>
    </>
  );
}
