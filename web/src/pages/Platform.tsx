import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Activity, ArrowRight, BadgeCheck, Brain, CalendarClock, Eye, FlaskConical, Headset, MessageSquareText, Microscope,
  ScanSearch, ShieldCheck, Users } from "lucide-react";
import { api, type Sample } from "../api";

const rise = (delay = 0) => ({ initial: { opacity: 0, y: 18 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.6, delay, ease: [0.2, 0.7, 0.2, 1] as const } });

const CATS = [
  { to: "/brain-mri", icon: Brain, title: "Brain tumour MRI", text: "Glioma, meningioma, pituitary tumour or none, with a lesion outline." },
  { to: "/colorectal", icon: Microscope, title: "Colorectal tissue", text: "Nine H&E tissue types with calibrated confidence and Grad-CAM." },
  { to: "/assistant", icon: MessageSquareText, title: "AI Assistant", text: "Explains any result and its uncertainty; medical questions only." },
  { to: "/appointments", icon: CalendarClock, title: "Appointments", text: "Refer a case to the right specialist, urgent cases first." },
];
const BAND = [[BadgeCheck, "99.3%", "Brain MRI test accuracy"], [ScanSearch, "95.1%", "Colorectal accuracy"],
  [ShieldCheck, "100%", "Colorectal tumour recall"], [FlaskConical, "10,793", "MRI slices studied"]] as const;
const FEATURED = [
  { page: "/brain-mri", sample: "glioma_axial_t1.jpg", img: "/static/brain-samples/glioma_axial_t1.jpg", title: "Glioma", tag: "Axial T1 MRI" },
  { page: "/brain-mri", sample: "meningioma_coronal_sample.png", img: "/static/brain-samples/meningioma_coronal_sample.png", title: "Meningioma", tag: "Coronal MRI" },
  { page: "/colorectal", sample: "test_colorectal_adenocarcinoma_epithelium_0.png", img: "/static/crc-samples/test_colorectal_adenocarcinoma_epithelium_0.png",
    title: "Adenocarcinoma", tag: "H&E tissue patch" },
  { page: "/colorectal", sample: "mosaic_16_patches_tumour_on_diagonal.jpg", img: "/static/crc-samples/mosaic_16_patches_tumour_on_diagonal.jpg",
    title: "16-patch mosaic", tag: "Whole-field tile scan" },
];

export default function Platform() {
  const navigate = useNavigate();
  const [samples, setSamples] = useState<{ brain: Sample[]; colorectal: Sample[] }>({ brain: [], colorectal: [] });
  const [mod, setMod] = useState<"brain" | "colorectal">("brain");
  const [pick, setPick] = useState("");
  useEffect(() => { api.get<{ brain: Sample[]; colorectal: Sample[] }>("/api/samples").then(setSamples).catch(() => {}); }, []);
  const list = samples[mod];
  const page = mod === "brain" ? "/brain-mri" : "/colorectal";
  const open = (to: string, sample?: string) => navigate(to, sample ? { state: { sample } } : undefined);

  return (
    <div className="landing">
      <section className="panel l-hero">
        <div>
          <motion.h1 {...rise(0)}>Clinical Intelligence Platform for <span>medical imaging</span></motion.h1>
          <motion.p className="sub" {...rise(0.08)}>Explainable AI for brain tumour MRI and colorectal pathology: a prediction you can check, the evidence behind it,
            and the right specialist next.</motion.p>
          <motion.div className="l-feats" {...rise(0.16)}>
            <div className="l-feat"><div className="ic"><ShieldCheck size={22} /></div><span><b>Validated</b><br />on held-out patients</span></div>
            <div className="l-feat"><div className="ic"><Eye size={22} /></div><span><b>Explainable</b><br />heatmaps and outlines</span></div>
            <div className="l-feat"><div className="ic"><Users size={22} /></div><span><b>Patient care</b><br />focused triage</span></div>
          </motion.div>
          <motion.div className="row" {...rise(0.24)}>
            <button className="btn primary lg" onClick={() => open("/brain-mri")}>Analyse a brain MRI <ArrowRight size={18} /></button>
            <button className="btn outline lg" onClick={() => open("/colorectal")}>Analyse tissue</button>
          </motion.div>
        </div>

        <motion.div className="scanbox" initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.9, delay: 0.15, ease: [0.2, 0.7, 0.2, 1] }}>
          <div className="frame">
            <img src="/static/assets/hero_mri.jpg" alt="Coronal T1 brain MRI slice" />
            <img className="ovl" src="/static/assets/hero_mri_overlay.jpg" alt="" />
            <span className="scan" />
            <span className="hud tl"><i className="rec" />Live analysis</span>
            <span className="hud tr">BRISC 2025 · T1 coronal</span>
          </div>
          <div className="chip-float one danger"><div className="ic"><Brain size={18} /></div><div><b>Meningioma 99.8%</b>5-fold CNN ensemble</div></div>
          <div className="chip-float two"><div className="ic"><Activity size={18} /></div><div><b>Triage 29 / 100</b>Routine review</div></div>
        </motion.div>
      </section>

      <motion.form className="panel quick" {...rise(0.1)} onSubmit={(e) => { e.preventDefault(); open(page, pick || list[0]?.name); }}>
        <div className="field"><span className="field-label">Modality</span>
          <div className="seg" role="radiogroup" aria-label="Modality">
            <button type="button" role="radio" aria-checked={mod === "brain"} className={mod === "brain" ? "on" : ""} onClick={() => { setMod("brain"); setPick(""); }}>Brain MRI</button>
            <button type="button" role="radio" aria-checked={mod === "colorectal"} className={mod === "colorectal" ? "on" : ""} onClick={() => { setMod("colorectal"); setPick(""); }}>Colorectal tissue</button>
          </div></div>
        <div className="field"><label className="field-label" htmlFor="pick">Test case</label>
          <select id="pick" className="input" value={pick} onChange={(e) => setPick(e.target.value)}>
            {list.map((s) => <option key={s.name} value={s.name}>{s.label} · {s.tag}</option>)}
          </select></div>
        <button className="btn primary lg">Analyse now</button>
      </motion.form>

      <motion.section className="panel l-about" {...rise()}>
        <div className="pics">
          <img src="/static/crc-samples/test_colorectal_adenocarcinoma_epithelium_1.png" alt="H&E tissue patch" />
          <img src="/static/brain-samples/pituitary_axial_sample.png" alt="Axial brain MRI" />
          <img src="/static/brain-samples/glioma_sagittal_sample.png" alt="Sagittal brain MRI" />
        </div>
        <div>
          <div className="kick">ABOUT MEDVISIONAI</div>
          <h2>Committed to evidence. <span>Dedicated to patients.</span></h2>
          <p>Every result comes with its reasons: calibrated confidence, the regions the model relied on, agreement between independent models,
            and a plain-language summary a specialist can act on. Built and validated on public datasets, for research use.</p>
          <Link className="btn primary" to="/benchmarks">See the validation <ArrowRight size={16} /></Link>
        </div>
      </motion.section>

      <section className="panel l-sec">
        <h2>What you can do</h2>
        <div className="cats">
          {CATS.map(({ to, icon: Icon, title, text }, i) => (
            <motion.div key={to} {...rise(i * 0.06)}><Link to={to} className="cat"><div className="ic"><Icon size={26} /></div><b>{title}</b><span>{text}</span></Link></motion.div>
          ))}
        </div>
      </section>

      <motion.section className="band" {...rise()}>
        <div><h2>Why MedVisionAI?</h2><p>Accuracy you can verify, explanations you can trust.</p></div>
        {BAND.map(([Icon, v, k]) => <div key={k} className="st"><Icon size={26} /><b>{v}</b><span>{k}</span></div>)}
      </motion.section>

      <section className="panel l-sec">
        <h2>Try a real test case</h2>
        <div className="feats">
          {FEATURED.map((f, i) => (
            <motion.div key={f.sample} className="feat" {...rise(i * 0.06)}>
              <div className="img"><img src={f.img} alt="" loading="lazy" /></div>
              <b>{f.title}</b><span>{f.tag}</span>
              <button className="btn outline sm" onClick={() => open(f.page, f.sample)}>Analyse</button>
            </motion.div>
          ))}
        </div>
      </section>

      <motion.section className="help" {...rise()}>
        <div className="ic"><Headset size={24} /></div>
        <div><b>Questions about a result?</b><span>The AI Assistant explains it in plain language, and a specialist is one referral away.</span></div>
        <Link className="btn" to="/assistant">Ask the assistant <ArrowRight size={16} /></Link>
      </motion.section>
    </div>
  );
}
