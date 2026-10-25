import { useCallback, useEffect, useState } from "react";
import { api, type Report } from "../api";
import { useStore } from "../store";
import { PageHead, Section, Seg } from "../components/ui";
import { fmt } from "./Appointments";

function Schedule({ r, onDone }: { r: Report; onDone: (msg: string) => void }) {
  const days = r.urgency === "urgent" ? 1 : r.urgency === "soon" ? 7 : 21;
  const d = new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);
  const [f, setF] = useState({ date: d, time: "09:00", location: `${r.department} outpatient clinic`, note: "" });
  const act = async (status: string) => {
    try {
      await api.patch(`/api/appointments/${r.id}`, status === "confirmed"
        ? { status, appointment_at: `${f.date}T${f.time}`, location: f.location, staff_note: f.note }
        : { status, staff_note: f.note || "Please contact the hospital." });
      onDone(`Request ${status}.`);
    } catch (e) { onDone(`Error: ${(e as Error).message}`); }
  };
  return (
    <details className="settings">
      <summary>Schedule or decline</summary>
      <div className="body">
        <label className="field"><span>Date</span><input className="input" type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></label>
        <label className="field"><span>Time</span><input className="input" type="time" step={900} value={f.time} onChange={(e) => setF({ ...f, time: e.target.value })} /></label>
        <label className="field"><span>Location / room</span><input className="input" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} /></label>
        <label className="field"><span>Note to the requester</span><input className="input" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
        <div className="row"><button className="btn primary" onClick={() => act("confirmed")}>Confirm appointment</button>
          <button className="btn" onClick={() => act("declined")}>Decline</button></div>
      </div>
    </details>
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
      <PageHead kicker="Hospital coordinators" title="Triage queue">
        Every appointment request, most urgent first and then oldest first. Confirm a date, time and room, or decline with a note; the
        requester sees the update immediately.
      </PageHead>
      <div className="counts">
        {[["Urgent waiting", pending.filter((r) => r.urgency === "urgent").length], ["Soon waiting", pending.filter((r) => r.urgency === "soon").length],
          ["Routine waiting", pending.filter((r) => r.urgency === "routine").length], ["Confirmed", rows.filter((r) => r.status === "confirmed").length]]
          .map(([k, v]) => <div key={k}><b>{v}</b><span>{k}</span></div>)}
      </div>
      {msg && <div className={`alert ${msg.startsWith("Error") ? "error" : "ok"}`}>{msg}</div>}
      <Section title={`${shown.length} request(s)`} note="urgent first, then oldest first" />
      <Seg value={view} onChange={setView} options={[["pending", "Waiting"], ["confirmed", "Confirmed"], ["all", "All"]]} />
      <div style={{ marginTop: 12 }}>
        {shown.length === 0 && <div className="muted small">Nothing here.</div>}
        {shown.map((r) => (
          <div key={r.id} className="req">
            <div className="hd">{r.position && <span className="chip pos">#{r.position}</span>}
              <span className={`chip ${r.urgency}`}>{config.urgency[r.urgency]?.label} · {config.urgency[r.urgency]?.target}</span>
              <span className={`chip ${r.status}`}>{config.statuses[r.status]}</span></div>
            <h4>{r.specialist} · {r.department}</h4>
            <div className="small muted">{r.organisation} · requested {fmt(r.created_at)}
              {r.status === "confirmed" && <> · <b>{fmt(r.appointment_at)}</b> · {r.location}</>}</div>
            <div className="kv">
              <span>Reason</span><div>{r.reason}</div><span>Preferred</span><div>{r.preferred || "—"}</div>
              <span>Patient ref.</span><div>{r.patient_ref || "—"}</div><span>Analysis</span><div>{r.case_summary || "—"}</div>
              <span>Contact</span><div>{r.requester_name} · {r.contact}</div>
            </div>
            {r.status === "pending" && <Schedule r={r} onDone={done} />}
            {r.status === "confirmed" && <button className="btn ghost" style={{ marginTop: 10 }}
              onClick={() => api.patch(`/api/appointments/${r.id}`, { status: "completed" }).then(() => done("Marked as completed.")).catch((e) => done(`Error: ${e.message}`))}>
              Mark as completed</button>}
          </div>
        ))}
      </div>
    </>
  );
}
