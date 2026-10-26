import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, KeyRound, X } from "lucide-react";
import { api, type Licence } from "../api";
import { useStore } from "../store";

/** Code field + submit. Used by the Activation page and the dialog. */
export function ActivationForm({ onDone, autoFocus }: { onDone?: () => void; autoFocus?: boolean }) {
  const { signIn } = useStore();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { if (autoFocus) ref.current?.focus(); }, [autoFocus]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const r = await api.post<{ token: string; licence: Licence }>("/api/auth/activate", { code });
      signIn(r.token, r.licence);
      setCode("");
      onDone?.();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <label className="field-label" htmlFor="code">Activation code</label>
      <input id="code" ref={ref} className="input code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="MVAI-XXXX-XXXX-XXXX-XXXX"
        autoComplete="off" spellCheck={false} maxLength={40} required />
      {error && <div className="alert danger" role="alert" style={{ marginTop: 12 }}><AlertCircle size={18} />{error}</div>}
      <button className="btn primary block lg" style={{ marginTop: 14 }} disabled={busy || !code.trim()}>
        <KeyRound size={18} />{busy ? "Checking…" : "Activate"}</button>
    </form>
  );
}

/** Opened by requireAuth() when an action needs a licence; continues the action after activation. */
export function ActivationDialog() {
  const { dialog, closeDialog, completeDialog } = useStore();
  useEffect(() => {
    if (!dialog.open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && closeDialog();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dialog.open, closeDialog]);
  return (
    <AnimatePresence>
      {dialog.open && (
        <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={closeDialog}>
          <motion.div className="dialog" role="dialog" aria-modal="true" aria-labelledby="act-title" onClick={(e) => e.stopPropagation()}
            initial={{ opacity: 0, y: 16, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 8 }} transition={{ duration: 0.25 }}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <img className="logo" src="/logo.svg" alt="" />
              <button className="icon-btn" onClick={closeDialog} aria-label="Close"><X size={18} /></button>
            </div>
            <h2 className="h2" id="act-title">Activate MedVisionAI</h2>
            <p>{dialog.reason || "Running analyses, the AI Assistant and referrals needs the activation code your organisation received. Everything else is open to explore."}</p>
            <ActivationForm onDone={completeDialog} autoFocus />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
