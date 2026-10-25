import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { useStore } from "../store";

const NAV: { section: string; items: { to: string; label: string; icon: string; open?: boolean; coord?: boolean }[] }[] = [
  { section: "Overview", items: [{ to: "/", label: "Platform", icon: "◧", open: true }] },
  { section: "Imaging analysis", items: [{ to: "/brain-mri", label: "Brain tumour MRI", icon: "◉" }, { to: "/colorectal", label: "Colorectal tissue", icon: "✣" }] },
  { section: "Clinical care", items: [{ to: "/assistant", label: "AI Assistant", icon: "❝" }, { to: "/appointments", label: "Book an appointment", icon: "◷" },
    { to: "/triage", label: "Triage queue", icon: "☰", coord: true }] },
  { section: "Research", items: [{ to: "/benchmarks", label: "Study & benchmarks", icon: "▤" }] },
  { section: "Account", items: [{ to: "/activation", label: "Activation", icon: "⚿", open: true }] },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { licence, signedIn, signOut, config } = useStore();
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => { setOpen(false); window.scrollTo(0, 0); }, [pathname]);
  const isCoord = licence?.role === "coordinator";

  return (
    <div className="shell">
      <aside className={`side${open ? " open" : ""}`} aria-label="Main navigation">
        <NavLink to="/" className="brand">
          <img src="/logo.svg" alt="" />
          <div><b>MEDVISIONAI</b><span>Clinical Intelligence Platform</span></div>
        </NavLink>
        <nav className="nav">
          {NAV.map((g) => {
            const items = g.items.filter((i) => !i.coord || isCoord);
            if (!items.length) return null;
            return (
              <div key={g.section} style={{ display: "contents" }}>
                <div className="nav-sec">{g.section}</div>
                {items.map((i) => (
                  <NavLink key={i.to} to={i.to} end={i.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}
                    title={!signedIn && !i.open ? "Enter an activation code to open this page" : undefined}>
                    <span className="ico" aria-hidden>{i.icon}</span>{i.label}
                    {!signedIn && !i.open && <span className="lock" aria-label="locked">🔒</span>}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        {licence ? (
          <div className="acct">
            <div className="k"><i />Licensed to</div>
            <div className="org">{licence.organisation}</div>
            <div className="meta">{licence.plan}{licence.expires ? ` · until ${licence.expires}` : ""}{isCoord ? " · coordinator" : ""}</div>
            <button onClick={signOut}>Sign out →</button>
          </div>
        ) : config && !config.licensing ? (
          <div className="acct"><div className="meta">Demo mode: licensing is off on this server.</div></div>
        ) : null}
        <div className="side-note"><b>Research use only.</b> Not a medical device. Results are not a diagnosis; always have images
          reviewed by a qualified specialist.</div>
      </aside>
      <div className="main">
        <div className="topbar"><span>MEDVISIONAI</span><button onClick={() => setOpen((o) => !o)} aria-label="Menu">Menu</button></div>
        <motion.div key={pathname} className="page" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.2, 0.7, 0.2, 1] }}>
            {children}
            <footer className="footer"><div><b>MedVisionAI</b> · Clinical Intelligence Platform for medical imaging</div>
              <div>Research prototype · not a medical device · not for diagnosis</div></footer>
        </motion.div>
      </div>
    </div>
  );
}
