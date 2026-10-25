import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Reveal, Section } from "../components/ui";

const INDEX = [
  ["I", "Brain tumour MRI", "Neuro-oncology · BRISC 2025", "/brain-mri",
    "Four CNNs read a T1 slice; a U-Net outlines the lesion; classical radiomics second-guess them; a 0–100 score suggests how soon a specialist should look."],
  ["II", "Colorectal tissue", "Histopathology · NCT-CRC-HE-100K", "/colorectal",
    "The Phikon foundation model sorts H&E patches into 9 tissue types with calibrated confidence and a Grad-CAM map; large slides are read tile by tile."],
  ["III", "AI Assistant", "Medical questions only", "/assistant", "Attach any case and ask about it. It explains, it flags uncertainty, it never diagnoses."],
  ["IV", "Appointments & triage", "Urgent first", "/appointments",
    "Refer a case to neuro-oncology, neuroradiology or GI pathology; coordinators see the most urgent requests on top."],
  ["V", "Study & benchmarks", "Validation", "/benchmarks", "Every number on this page, with the tables and figures it came from."],
];

const PLATES = [
  ["I", "/brain-mri", "glioma_axial_t1.jpg", "/static/brain-samples/glioma_axial_t1.jpg", "Glioma, axial T1", "Brain MRI"],
  ["II", "/colorectal", "test_colorectal_adenocarcinoma_epithelium_0.png",
    "/static/crc-samples/test_colorectal_adenocarcinoma_epithelium_0.png", "Adenocarcinoma", "H&E patch"],
  ["III", "/brain-mri", "pituitary_coronal_sample.png", "/static/brain-samples/pituitary_coronal_sample.png", "Pituitary, coronal", "Brain MRI"],
];

const FIGS = [["99.3", "%", "brain MRI test accuracy, 5-fold ensemble, 1,000 held-out slices"],
  ["95.1", "%", "colorectal 9-class accuracy on 50 patients never seen in training"],
  ["100", "%", "colorectal tumour recall on the same external test set"],
  ["10,793", "n", "MRI slices in the BRISC 2025 comparative study"]];

const rise = (delay: number) => ({ initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 },
  transition: { duration: 0.8, delay, ease: [0.2, 0.7, 0.2, 1] as const } });

export default function Platform() {
  const navigate = useNavigate();
  return (
    <>
      <motion.div className="mast" {...rise(0)}>
        <span><b>MedVisionAI</b> · Clinical atlas</span><span>Radiology &amp; pathology · research edition</span><span>Not a medical device</span>
      </motion.div>
      <section className="hero">
        <div>
          <motion.span className="kicker" {...rise(0.05)}>Clinical intelligence · est. 2026</motion.span>
          <motion.h1 {...rise(0.12)}>Clinical Intelligence Platform for <em>medical imaging</em>.</motion.h1>
          <motion.p className="lede" {...rise(0.2)}>Read a brain MRI slice or an H&amp;E tissue patch the way a specialist would: see what the
            model predicts, where it looked, how sure it is, and who should review the case next.</motion.p>
          <motion.div className="cta" {...rise(0.28)}>
            <Link className="btn ghost" to="/brain-mri">Read a brain MRI →</Link>
            <Link className="btn ghost" to="/colorectal">Read a tissue slide →</Link>
          </motion.div>
        </div>
        <motion.figure className="lightbox" initial={{ clipPath: "inset(0 100% 0 0)" }} animate={{ clipPath: "inset(0 0% 0 0)" }}
          transition={{ duration: 1.2, delay: 0.2, ease: [0.7, 0, 0.2, 1] }}>
          <div className="frame">
            <img src="/static/assets/hero_mri.jpg" alt="Coronal T1 MRI slice" />
            <img className="ovl" src="/static/assets/hero_mri_overlay.jpg" alt="U-Net lesion outline" />
            <span className="scan" />
            <span className="hud tl">BRISC 2025 · test<br /><b>T1 · coronal</b></span>
            <span className="hud tr">809 × 808<br />U-Net · flip TTA</span>
            <span className="hud bl"><i className="rec" />Ensemble · 5 folds<br /><b>Meningioma 99.8%</b></span>
            <span className="hud br">Lesion 2.7% of slice<br /><b>Triage 29 / 100</b></span>
          </div>
          <figcaption><b>Fig. 1</b> — Meningioma on a coronal T1 slice. The lesion outline (gold) comes from the U-Net; the class from the
            5-fold EfficientNet ensemble. Real output of this platform.</figcaption>
        </motion.figure>
      </section>

      <Reveal className="figs">
        {FIGS.map(([v, u, t]) => <div key={t}><b>{v}<sup>{u}</sup></b><span>{t}</span></div>)}
      </Reveal>

      <Section title="Index" note="five rooms, one platform" />
      <div className="index">
        {INDEX.map(([n, title, k, to, text], i) => (
          <Reveal key={n} delay={0.06 * i}>
            <Link to={to}>
              <div className="n">{n}</div>
              <div><h3>{title}</h3><div className="k">{k}</div></div>
              <p>{text}</p>
              <div className="arr">→</div>
            </Link>
          </Reveal>
        ))}
      </div>

      <Section title="Plates" note="open a real test case in one click" />
      <div className="plates3">
        {PLATES.map(([n, to, sample, src, title, tag], i) => (
          <Reveal key={n} delay={0.08 * i}>
            <button className="pl" onClick={() => navigate(to, { state: { sample } })}>
              <div className="plate"><img src={src} alt="" /></div>
              <div className="cap"><b><i>Pl. {n}</i>{title}</b><span>{tag} →</span></div>
            </button>
          </Reveal>
        ))}
      </div>
    </>
  );
}
