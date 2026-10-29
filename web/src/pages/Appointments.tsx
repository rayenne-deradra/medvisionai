import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CalendarClock, CheckCircle2, KeyRound, Siren } from "lucide-react";
import { api, type Report } from "../api";
import { caseLabel, useStore } from "../store";
import { PageHead, SectionHead } from "../components/ui";

export function fmt(value?: string | null) {
  if (!value) return "";
  const d = new Date(value);
  return isNaN(d.getTime()) ? value : d.toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Appointments() {
  const { config, cases, signedIn, requireAuth } = useStore();
  const location = useLocation();
  const state = (location.state || {}) as { caseId?: string; specialist?: string };
  const [sid, setSid] = useState<string | null>(state.specialist || null);
  const [caseId, setCaseId] = useState(state.caseId || "");
  const [form, setForm] = useState({ urgency: "routine", reason: "", requester: "", contact: "", preferred: "", patient_ref: "", consent: false });
  const [suggested, setSuggested] = useState<string | null>(null);
  const [mine, setMine] = useState<Report[]>([]);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [sending, setSending] = useState(false);

  const load = useCallback(() => { if (signedIn) api.get<{ mine: Report[] }>("/api/appointments").then((r) => setMine(r.mine)).catch(() => {}); }, [signedIn]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!caseId || !signedIn) { setSuggested(null); return; }
    api.get<{ urgency: string }>(`/api/appointments/suggest?case_id=${caseId}`)
      .then((s) => { setSuggested(s.urgency); setForm((f) => ({ ...f, urgency: s.urgency })); }).catch(() => setSuggested(null));
  }, [caseId, signedIn]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sid) return;
    requireAuth(async () => {
      setSending(true); setMsg(null);
      try {
        const row = await api.post<Report>("/api/appointments", { ...form, specialist_id: sid, case_id: caseId || null });
        setMsg({ ok: true, text: `Request sent to the ${row.specialist.toLowerCase()} (${config?.urgency[row.urgency].label.toLowerCase()}). You are number ${row.position} in the queue; urgent requests are seen first.` });
        setSid(null); setForm((f) => ({ ...f, reason: "", consent: false })); load();
      } catch (err) {
        setMsg({ ok: false, text: (err as Error).message });
      } finally {
        setSending(false);
      }
    }, "Sending a referral needs your organisation's activation code.");
  };

  const cancel = async (id: string) => {
    try { await api.patch(`/api/appointments/${id}`, { status: "cancelled" }); load(); } catch (err) { setMsg({ ok: false, text: (err as Error).message }); load(); }
  };

  if (!config) return null;
  const spec = config.specialists.find((s) => s.id === sid);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });
  return (
    <>
      <PageHead icon={<CalendarClock size={16} />} eyebrow={config.hospital} title="Appointments">
        Request an in-person consultation with a specialist. Urgent cases are seen first, then by time of request, and a coordinator confirms the date, time and room.
      </PageHead>
      <div className="alert danger"><Siren size={18} /><span><b>Medical emergency?</b> Call your local emergency number (112 or 911) or go to the nearest emergency department. Requests are not monitored around the clock.</span></div>

      <SectionHead title="1. Choose a specialist" note={config.persistent_appointments ? undefined : "Demo mode: requests are kept until the server restarts."} />
      <div className="specs">
        {config.specialists.map((s) => (
          <button key={s.id} className={`spec${sid === s.id ? " on" : ""}`} onClick={() => { setSid(s.id); setMsg(null); }} aria-pressed={sid === s.id}>
            <div className="av">{s.badge}</div>
            <div><b>{s.title}</b><small>{s.department}</small><p>{s.focus}</p></div>
          </button>
        ))}
      </div>

      {msg && <div className={`alert ${msg.ok ? "success" : "danger"}`} style={{ marginTop: 16 }}>{msg.ok ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}{msg.text}</div>}
      <AnimatePresence>
        {spec && (
          <motion.form key={spec.id} onSubmit={submit} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <SectionHead title="2. Request details" note={`${spec.title} · ${spec.department}`} />
            <div className="card pad-lg">
              <div className="grid-2">
                <div className="field"><label className="field-label" htmlFor="case">Attach an analysis (optional)</label>
                  <select id="case" className="input" value={caseId} onChange={(e) => setCaseId(e.target.value)}>
                    <option value="">No analysis</option>{cases.map((c) => <option key={c.id} value={c.id}>{caseLabel(c)}</option>)}</select>
                  <div className="hint">Only a short text summary is shared, never the images.</div></div>
                <div className="field"><span className="field-label">Urgency{suggested && <span className="muted"> · suggested: {config.urgency[suggested].label}</span>}</span>
                  <div className="seg" role="radiogroup" aria-label="Urgency">
                    {Object.entries(config.urgency).map(([k, u]) => (
                      <button key={k} type="button" role="radio" aria-checked={form.urgency === k} className={form.urgency === k ? "on" : ""}
                        onClick={() => setForm({ ...form, urgency: k })} title={u.description}>{u.label}</button>))}
                  </div><div className="hint">{config.urgency[form.urgency].target}: {config.urgency[form.urgency].description}</div></div>
              </div>
              <div className="field"><label className="field-label" htmlFor="reason">Reason for the consultation</label>
                <textarea id="reason" className="input" value={form.reason} onChange={set("reason")} required maxLength={2000}
                  placeholder="What should the specialist look at? Relevant history and what has been done so far." /></div>
              <div className="grid-2">
                <div className="field"><label className="field-label" htmlFor="who">Contact person</label><input id="who" className="input" value={form.requester} onChange={set("requester")} required maxLength={120} /></div>
                <div className="field"><label className="field-label" htmlFor="contact">Phone or email</label><input id="contact" className="input" value={form.contact} onChange={set("contact")} required maxLength={120} /></div>
                <div className="field"><label className="field-label" htmlFor="pref">Preferred days or times</label><input id="pref" className="input" value={form.preferred} onChange={set("preferred")} maxLength={300} placeholder="e.g. weekday mornings" /></div>
                <div className="field"><label className="field-label" htmlFor="ref">Patient reference</label><input id="ref" className="input" value={form.patient_ref} onChange={set("patient_ref")} maxLength={60} placeholder="Internal ID only, no names" /></div>
              </div>
              <label className="switch" style={{ borderTop: "1px solid var(--border)", marginTop: 4 }}>
                <span>The patient agreed to this referral<small>and I have not entered unnecessary identifying details.</small></span>
                <input type="checkbox" role="switch" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} /></label>
              <button className="btn primary lg" style={{ marginTop: 12 }} disabled={sending || !form.consent}>{sending ? "Sending…" : "Send request"}</button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      <SectionHead title="My requests" note={signedIn ? `${mine.length} request${mine.length === 1 ? "" : "s"}` : undefined} />
      <div className="card">
        {!signedIn ? (
          <div className="row" style={{ justifyContent: "space-between" }}><span className="muted">Activate to see your requests and their place in the queue.</span>
            <button className="btn primary sm" onClick={() => requireAuth(load)}><KeyRound size={15} />Activate</button></div>
        ) : mine.length === 0 ? <span className="muted">No requests yet.</span> : mine.map((r) => (
          <div key={r.id} className="list-item">
            <div>
              <div className="row"><span className={`badge ${r.urgency}`}>{config.urgency[r.urgency]?.label}</span><span className={`badge ${r.status}`}>{config.statuses[r.status]}</span>
                {r.status === "pending" && r.position && <span className="badge solid">#{r.position} in queue</span>}</div>
              <h4>{r.specialist}</h4>
              <div className="small muted">Requested {fmt(r.created_at)} by {r.requester_name}</div>
              {r.status === "confirmed" && <div style={{ marginTop: 6 }}><b>{fmt(r.appointment_at)}</b>{r.location ? ` · ${r.location}` : ""}</div>}
              {r.staff_note && <div className="alert info" style={{ marginTop: 8 }}>Hospital note: {r.staff_note}</div>}
            </div>
            {["pending", "confirmed"].includes(r.status) && <button className="btn quiet sm" onClick={() => cancel(r.id)}>Cancel</button>}
          </div>
        ))}
      </div>
    </>
  );
}
