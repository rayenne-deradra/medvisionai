import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, ClipboardList } from "lucide-react";
import { api, type Report } from "../api";
import { useStore } from "../store";
import { PageHead, Seg } from "../components/ui";
import { fmt } from "./Appointments";

function Schedule({ r, onDone }: { r: Report; onDone: (msg: string) => void }) {
  const days = r.urgency === "urgent" ? 1 : r.urgency === "soon" ? 7 : 21;
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ date: new Date(Date.now() + days * 86400000).toISOString().slice(0, 10), time: "09:00",
    location: `${r.department} outpatient clinic`, note: "" });
  const act = async (status: string) => {
    try {
      await api.patch(`/api/appointments/${r.id}`, status === "confirmed"
        ? { status, appointment_at: `${f.date}T${f.time}`, location: f.location, staff_note: f.note }
        : { status, staff_note: f.note || "Please contact the hospital." });
      onDone(`Request ${status}.`);
    } catch (e) { onDone(`Error: ${(e as Error).message}`); }
  };
  if (!open) return <button className="btn sm" onClick={() => setOpen(true)}>Schedule or decline</button>;
  return (
    <div className="card" style={{ marginTop: 12, background: "var(--surface-2)" }}>
      <div className="grid-2">
        <div className="field"><label className="field-label">Date</label><input className="input" type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></div>
        <div className="field"><label className="field-label">Time</label><input className="input" type="time" step={900} value={f.time} onChange={(e) => setF({ ...f, time: e.target.value })} /></div>
        <div className="field"><label className="field-label">Location or room</label><input className="input" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} /></div>
        <div className="field"><label className="field-label">Note to the requester</label><input className="input" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></div>
      </div>
      <div className="row"><button className="btn primary" onClick={() => act("confirmed")}>Confirm appointment</button>
        <button className="btn" onClick={() => act("declined")}>Decline</button><button className="btn quiet" onClick={() => setOpen(false)}>Close</button></div>
    </div>
  );
}

export default function Triage() {
  const { config } = useStore();
  const [rows, setRows] = useState<Report[]>([]);
  const [view, setView] = useState("pending");
  const [msg, setMsg] = useState("");
  const load = useCallback(() => api.get<{ queue?: Report[] }>("/api/appointments").then((r) => setRows(r.queue || [])).catch((e) => setMsg(`Error: ${e.message}`)), []);
  useEffect(() => { load(); }, [load]);
  if (!config) return null;
  const pending = rows.filter((r) => r.status === "pending");
  const shown = view === "all" ? rows : rows.filter((r) => r.status === view);
  const done = (m: string) => { setMsg(m); load(); };
  return (
    <>
      <PageHead icon={<ClipboardList size={16} />} eyebrow="Hospital coordinators" title="Triage queue">
        Every request, most urgent first and then oldest first. Confirm a date, time and room, or decline with a note; the requester sees the update immediately.
      </PageHead>
      <div className="stats" style={{ marginTop: 0 }}>
        {[["Urgent waiting", pending.filter((r) => r.urgency === "urgent").length], ["Soon waiting", pending.filter((r) => r.urgency === "soon").length],
          ["Routine waiting", pending.filter((r) => r.urgency === "routine").length], ["Confirmed", rows.filter((r) => r.status === "confirmed").length]]
          .map(([k, v]) => <div key={k} className="card stat"><b>{v}</b><span>{k}</span></div>)}
      </div>
      {msg && <div className={`alert ${msg.startsWith("Error") ? "danger" : "success"}`} style={{ marginTop: 16 }}>
        {msg.startsWith("Error") ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}{msg}</div>}
      <div className="row" style={{ justifyContent: "space-between", margin: "28px 0 12px" }}>
        <h2 className="h2">{shown.length} request{shown.length === 1 ? "" : "s"}</h2>
        <div style={{ width: 300 }}><Seg label="Show" value={view} onChange={setView} options={[["pending", "Waiting"], ["confirmed", "Confirmed"], ["all", "All"]]} /></div>
      </div>
      <div className="card">
        {shown.length === 0 && <span className="muted">Nothing here.</span>}
        {shown.map((r) => (
          <div key={r.id} className="list-item" style={{ gridTemplateColumns: "1fr" }}>
            <div>
              <div className="row">{r.position && <span className="badge solid">#{r.position}</span>}
                <span className={`badge ${r.urgency}`}>{config.urgency[r.urgency]?.label} · {config.urgency[r.urgency]?.target}</span>
                <span className={`badge ${r.status}`}>{config.statuses[r.status]}</span></div>
              <h4>{r.specialist} · {r.department}</h4>
              <div className="small muted">{r.organisation} · requested {fmt(r.created_at)}{r.status === "confirmed" && <> · <b>{fmt(r.appointment_at)}</b> · {r.location}</>}</div>
              <dl className="detail">
                <dt>Reason</dt><dd>{r.reason}</dd><dt>Preferred</dt><dd>{r.preferred || "—"}</dd><dt>Patient ref.</dt><dd>{r.patient_ref || "—"}</dd>
                <dt>Analysis</dt><dd>{r.case_summary || "—"}</dd><dt>Contact</dt><dd>{r.requester_name} · {r.contact}</dd>
              </dl>
              <div style={{ marginTop: 12 }}>
                {r.status === "pending" && <Schedule r={r} onDone={done} />}
                {r.status === "confirmed" && <button className="btn sm" onClick={() => api.patch(`/api/appointments/${r.id}`, { status: "completed" })
                  .then(() => done("Marked as completed.")).catch((e) => done(`Error: ${e.message}`))}>Mark as completed</button>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
