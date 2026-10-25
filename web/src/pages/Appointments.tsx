import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, type Report } from "../api";
import { caseLabel, useStore } from "../store";
import { PageHead, Section } from "../components/ui";

export function fmt(value?: string | null) {
  if (!value) return "";
  const d = new Date(value);
  return isNaN(d.getTime()) ? value : d.toLocaleString(undefined, { weekday: "short", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Appointments() {
  const { config, cases } = useStore();
  const location = useLocation();
  const state = (location.state || {}) as { caseId?: string; specialist?: string };
  const [sid, setSid] = useState<string | null>(state.specialist || null);
  const [caseId, setCaseId] = useState(state.caseId || "");
  const [form, setForm] = useState({ urgency: "routine", reason: "", requester: "", contact: "", preferred: "", patient_ref: "", consent: false });
  const [suggested, setSuggested] = useState<string | null>(null);
  const [mine, setMine] = useState<Report[]>([]);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [sending, setSending] = useState(false);

  const load = useCallback(() => api.get<{ mine: Report[] }>("/api/appointments").then((r) => setMine(r.mine)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!caseId) { setSuggested(null); return; }
    api.get<{ urgency: string }>(`/api/appointments/suggest?case_id=${caseId}`)
      .then((s) => { setSuggested(s.urgency); setForm((f) => ({ ...f, urgency: s.urgency })); }).catch(() => setSuggested(null));
  }, [caseId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!sid) return;
    setSending(true); setMsg(null);
    try {
      const row = await api.post<Report>("/api/appointments", { ...form, specialist_id: sid, case_id: caseId || null });
      setMsg({ ok: true, text: `Request sent to ${row.specialist} (${config?.urgency[row.urgency].label}). You are number ${row.position} in the line; urgent requests are seen first.` });
      setSid(null); setForm((f) => ({ ...f, reason: "", consent: false })); load();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    } finally {
      setSending(false);
    }
  }

  async function cancel(id: string) {
    try { await api.patch(`/api/appointments/${id}`, { status: "cancelled" }); load(); } catch (err) { setMsg({ ok: false, text: (err as Error).message }); }
  }

  if (!config) return null;
  const spec = config.specialists.find((s) => s.id === sid);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });
  return (
    <>
      <PageHead kicker={`Hospital appointments · ${config.hospital}`} title="Book an appointment">
        Request an in-person consultation with a specialist. Every request is triaged: <b>urgent cases are seen first</b>, then by time of
        request. A coordinator confirms the date, time and room.
      </PageHead>
      <div className="alert error" style={{ marginTop: 16 }}><b>Medical emergency?</b> Call your local emergency number (112 or 911) or go to the
        nearest emergency department. Requests are not monitored around the clock.</div>
      {!config.persistent_appointments && <div className="foot">Demo mode: requests are kept until the server restarts.</div>}

      <Section title="Choose a specialist" note={`in person at ${config.hospital}`} />
      <div className="specs">
        {config.specialists.map((s, i) => (
          <motion.button key={s.id} className={`spec${sid === s.id ? " on" : ""}`} onClick={() => { setSid(s.id); setMsg(null); }}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 * i }}>
            <div className="top"><div className="av">{s.badge}</div><span className="dept">{s.department}</span></div>
            <h4>{s.title}</h4><p>{s.focus}</p>
          </motion.button>
        ))}
      </div>

      {msg && <div className={`alert ${msg.ok ? "ok" : "error"}`} style={{ marginTop: 16 }}>{msg.text}</div>}
      <AnimatePresence>
        {spec && (
          <motion.form key={spec.id} onSubmit={submit} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <Section title="Request details" note={`${spec.title} · ${spec.department}`} />
            <div className="card">
              <label className="field"><span>Attach an analysis summary (optional; images are never shared)</span>
                <select className="input" value={caseId} onChange={(e) => setCaseId(e.target.value)}>
                  <option value="">No analysis</option>
                  {cases.map((c) => <option key={c.id} value={c.id}>{caseLabel(c)}</option>)}
                </select></label>
              <div className="field"><span>Urgency{suggested ? ` · suggested: ${config.urgency[suggested].label}` : ""}</span>
                <div className="row">
                  {Object.entries(config.urgency).map(([k, u]) => (
                    <label key={k} className="toggle" style={{ marginBottom: 0 }}><input type="radio" name="urg" checked={form.urgency === k}
                      onChange={() => setForm({ ...form, urgency: k })} /><span className={`chip ${k}`}>{u.label}</span> {u.target}</label>
                  ))}
                </div></div>
              <label className="field"><span>Reason for the consultation</span>
                <textarea className="input" value={form.reason} onChange={set("reason")} required maxLength={2000}
                  placeholder="What should the specialist look at? Relevant history, what has been done so far." /></label>
              <div className="grid2" style={{ gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <label className="field"><span>Contact person</span><input className="input" value={form.requester} onChange={set("requester")} required maxLength={120} placeholder="Dr. Name or coordinator" /></label>
                <label className="field"><span>Phone or e-mail</span><input className="input" value={form.contact} onChange={set("contact")} required maxLength={120} /></label>
                <label className="field"><span>Preferred days / times</span><input className="input" value={form.preferred} onChange={set("preferred")} maxLength={300} placeholder="e.g. weekday mornings" /></label>
                <label className="field"><span>Patient reference (internal ID only)</span><input className="input" value={form.patient_ref} onChange={set("patient_ref")} maxLength={60} /></label>
              </div>
              <label className="toggle"><input type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} />
                I confirm the patient agreed to this referral and I have not entered unnecessary identifying details.</label>
              <button className="btn primary" disabled={sending || !form.consent}>{sending ? "Sending…" : "Send request"}</button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      <Section title="My requests" note={`${mine.length} request(s)`} />
      {mine.length === 0 && <div className="muted small">No requests yet.</div>}
      {mine.map((r) => (
        <div key={r.id} className="req">
          <div className="hd"><span className={`chip ${r.urgency}`}>{config.urgency[r.urgency]?.label}</span>
            <span className={`chip ${r.status}`}>{config.statuses[r.status]}</span>
            {r.status === "pending" && r.position && <span className="chip pos">#{r.position} in line</span>}</div>
          <h4>{r.specialist}</h4>
          <div className="small muted">Requested {fmt(r.created_at)} by {r.requester_name}</div>
          {r.status === "confirmed" && <div style={{ marginTop: 6 }}><b>{fmt(r.appointment_at)}</b>{r.location ? ` · ${r.location}` : ""}</div>}
          {r.staff_note && <div className="alert info" style={{ marginTop: 8 }}>Hospital note: {r.staff_note}</div>}
          {["pending", "confirmed"].includes(r.status) && <button className="btn ghost" style={{ marginTop: 8 }} onClick={() => cancel(r.id)}>Cancel request</button>}
        </div>
      ))}
    </>
  );
}
