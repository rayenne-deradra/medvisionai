import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { api, type Licence } from "../api";
import { useStore } from "../store";

export default function Activation() {
  const { config, licence, signIn, signOut } = useStore();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [switching, setSwitching] = useState(false);

  async function activate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const r = await api.post<{ token: string; licence: Licence }>("/api/auth/activate", { code });
      signIn(r.token, r.licence);
      setCode("");
      navigate(params.get("next") || "/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const form = (
    <form onSubmit={activate}>
      <label className="field"><span>Activation code</span>
        <input className="input code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="MVAI-XXXX-XXXX-XXXX-XXXX"
          autoComplete="off" spellCheck={false} maxLength={40} required /></label>
      <button className="btn primary block" disabled={busy}>{busy ? "Checking…" : "Activate"}</button>
      {error && <div className="alert error" style={{ marginTop: 12 }}>{error}</div>}
    </form>
  );

  return (
    <motion.div className="login" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4 }}>
      <div className="card">
        <img className="logo" src="/logo.svg" alt="" />
        <div style={{ textAlign: "center" }}><span className="kicker">MedVisionAI · Account</span></div>
        {licence ? (
          <>
            <h1>Licence active</h1>
            <p>Licensed to <b>{licence.organisation}</b></p>
            <div className="kv" style={{ marginBottom: 18 }}>
              <span>Plan</span><div>{licence.plan || "—"}</div>
              <span>Valid until</span><div>{licence.expires || "no expiry"}</div>
              <span>Access</span><div>{licence.role === "coordinator" ? "Hospital coordinator" : "Clinical user"}</div>
            </div>
            {switching ? form : <div className="row">
              <button className="btn" onClick={() => setSwitching(true)}>Use a different code</button>
              <button className="btn ghost" onClick={signOut}>Sign out</button></div>}
          </>
        ) : config && !config.licensing ? (
          <><h1>Demo mode</h1><p>Licensing is not configured on this server, so every page is open without a code.</p></>
        ) : (
          <><h1>Activate your licence</h1><p>Enter the activation code your organisation received from MedVisionAI.</p>{form}</>
        )}
        <div className="foot" style={{ textAlign: "center", marginTop: 18 }}><b>How do I get a code?</b> Codes are issued to hospitals, laboratories
          and research groups once their subscription is confirmed. Each code is linked to an organisation and has an expiry date.</div>
      </div>
    </motion.div>
  );
}
