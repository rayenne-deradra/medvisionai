import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { BarChart3, Brain, CalendarClock, ChevronRight, ClipboardList, KeyRound, LayoutDashboard, LogOut, Menu, MessageSquareText,
  Microscope, PanelLeftClose, PanelLeftOpen, ShieldCheck } from "lucide-react";
import { useStore } from "../store";
import { ActivationDialog } from "./ActivationForm";

const NAV = [
  { group: "Overview", items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }] },
  { group: "Imaging", items: [{ to: "/brain-mri", label: "Brain tumour MRI", icon: Brain }, { to: "/colorectal", label: "Colorectal tissue", icon: Microscope }] },
  { group: "Care", items: [{ to: "/assistant", label: "AI Assistant", icon: MessageSquareText }, { to: "/appointments", label: "Appointments", icon: CalendarClock },
    { to: "/triage", label: "Triage queue", icon: ClipboardList, coordinator: true }] },
  { group: "Research", items: [{ to: "/benchmarks", label: "Study & benchmarks", icon: BarChart3 }] },
  { group: "Account", items: [{ to: "/activation", label: "Activation", icon: KeyRound }] },
];
const TITLES: Record<string, string> = { "/": "Dashboard", "/brain-mri": "Brain tumour MRI", "/colorectal": "Colorectal tissue", "/assistant": "AI Assistant",
  "/appointments": "Appointments", "/triage": "Triage queue", "/benchmarks": "Study & benchmarks", "/activation": "Activation" };
const KEY = "mvai_sidebar";

export default function Layout({ children }: { children: ReactNode }) {
  const { licence, signedIn, signOut, config, requireAuth } = useStore();
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem(KEY) === "collapsed"; } catch { return false; } });
  const [open, setOpen] = useState(false);
  useEffect(() => { setOpen(false); window.scrollTo(0, 0); }, [pathname]);
  useEffect(() => { try { localStorage.setItem(KEY, collapsed ? "collapsed" : "open"); } catch { /* ignore */ } }, [collapsed]);
  useEffect(() => {      // "[" toggles the sidebar, like in many desktop apps
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (e.key === "[" && !["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName)) setCollapsed((c) => !c);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const isCoord = licence?.role === "coordinator";

  return (
    <div className={`shell${collapsed ? " collapsed" : ""}${open ? " open" : ""}`}>
      <aside className="side" aria-label="Main navigation">
        <div className="side-head">
          <NavLink to="/" className="brand" aria-label="MedVisionAI dashboard">
            <img src="/logo.svg" alt="" /><span className="brand-name">MedVision<span>AI</span></span>
          </NavLink>
          <button className="icon-btn collapse-btn" onClick={() => setCollapsed((c) => !c)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar  [" : "Collapse sidebar  ["}>
            {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
          </button>
        </div>
        <nav className="nav">
          {NAV.map((g) => {
            const items = g.items.filter((i) => !("coordinator" in i) || isCoord);
            return (
              <div key={g.group} style={{ display: "contents" }}>
                <div className="nav-group">{g.group}</div>
                {items.map(({ to, label, icon: Icon }) => (
                  <NavLink key={to} to={to} end={to === "/"} data-label={label} aria-label={label} className={({ isActive }) => (isActive ? "active" : "")}>
                    <Icon size={19} /><span className="label-txt">{label}</span>
                    {to === "/activation" && !signedIn && <span className="tag">Needed</span>}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        <div className="side-foot">
          {licence ? (
            <>
              <div className="licence" title={`Licensed to ${licence.organisation}`}><div className="dot"><ShieldCheck size={17} /></div>
                <div className="txt"><b>{licence.organisation}</b>{isCoord ? "Coordinator" : licence.plan || "Licensed"}</div></div>
              <button className="btn quiet sm" style={{ color: "#A9AECF", justifyContent: "flex-start" }} onClick={signOut} aria-label="Sign out">
                <LogOut size={16} /><span className="txt">Sign out</span></button>
            </>
          ) : (
            <div className="licence"><div className="dot"><KeyRound size={17} /></div>
              <div className="txt"><b>{config && (!config.licensing || config.open_access) ? "Open demo access" : "Not activated"}</b>Research prototype</div></div>
          )}
        </div>
      </aside>
      <div className="scrim" onClick={() => setOpen(false)} />

      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={20} /></button>
          <div className="crumb">MedVisionAI <ChevronRight size={15} /> <b>{TITLES[pathname] || "MedVisionAI"}</b></div>
          <div className="spacer" />
          {licence ? (
            <span className="badge success"><ShieldCheck size={14} />Activated</span>
          ) : signedIn ? (
            config?.licensing && <Link className="btn quiet sm" to="/activation"><KeyRound size={15} />Have a code?</Link>
          ) : (
            <button className="btn primary sm" onClick={() => requireAuth()}><KeyRound size={15} />Activate</button>
          )}
        </header>
        <motion.main key={pathname} className="page" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          {children}
        </motion.main>
        <footer className="footer"><span>MedVisionAI · Clinical Intelligence Platform for medical imaging</span>
          <span>Research prototype. Not a medical device and not for diagnosis.</span></footer>
      </div>
      <ActivationDialog />
    </div>
  );
}
