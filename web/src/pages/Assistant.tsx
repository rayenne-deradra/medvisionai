import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { motion } from "framer-motion";
import { api } from "../api";
import { caseLabel, useStore, type ChatMsg } from "../store";
import { PageHead } from "../components/ui";

const SUGGESTIONS = [
  "How do glioma, meningioma and pituitary tumours differ on brain MRI?",
  "What are the early warning signs of colorectal cancer?",
  "How should I interpret a Grad-CAM heatmap on a tissue patch?",
  "What does a U-Net lesion outline on an MRI slice tell me, and what not?",
];

export default function Assistant() {
  const { config, cases, messages, setMessages, pendingCase, setPendingCase } = useStore();
  const [text, setText] = useState("");
  const [attach, setAttach] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const autoSent = useRef(false);

  async function send(content: string, caseId: string | null) {
    if (busy || !content.trim()) return;
    const c = cases.find((x) => x.id === caseId);
    const history = [...messages.filter((m) => !m.error), { role: "user" as const, content }];
    setMessages((m) => [...m, { role: "user", content, caseLabel: c ? caseLabel(c) : undefined }, { role: "assistant", content: "" }]);
    setText(""); setAttach(""); setBusy(true);
    const update = (fn: (last: ChatMsg) => ChatMsg) => setMessages((m) => [...m.slice(0, -1), fn(m[m.length - 1])]);
    try {
      await api.chat({ messages: history.map(({ role, content }) => ({ role, content })), case_id: caseId },
        (full) => update((last) => ({ ...last, content: full })));
    } catch (e) {
      update(() => ({ role: "assistant", content: (e as Error).message, error: true }));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (pendingCase && !autoSent.current) {
      autoSent.current = true;
      setPendingCase(null);
      send("Please explain this MedVisionAI analysis.", pendingCase);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingCase]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages]);

  const offline = config && !config.ai;
  return (
    <>
      <PageHead kicker="Clinical copilot · medical questions only" title="AI Assistant">
        Ask about brain MRI, colorectal pathology or any of your analyses. It explains results and their uncertainty; it never gives a diagnosis.
      </PageHead>
      {offline && <div className="alert warn" style={{ marginTop: 16 }}>The assistant is offline on this server: no OpenAI or Gemini key is configured.
        Image analysis still works.</div>}

      <div className="chat" style={{ marginTop: 22 }}>
        {messages.length === 0 && !offline && (
          <div className="suggest">
            {SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s, null)}>{s}</button>)}
          </div>
        )}
        {messages.map((m, i) => (
          <motion.div key={i} className={`msg ${m.role}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
            style={m.error ? { borderColor: "#F3C4CA", background: "var(--rose-bg)", color: "#8E2B37" } : undefined}>
            {m.role === "assistant" && <div className="who">MedVisionAI</div>}
            {m.caseLabel && <div className="att"><span>📎 {m.caseLabel}</span></div>}
            {m.role === "assistant" && !m.content && busy && i === messages.length - 1
              ? <div className="typing"><span /><span /><span /></div>
              : m.role === "assistant" ? <Markdown>{m.content}</Markdown> : <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>}
          </motion.div>
        ))}
        <div ref={bottom} />
      </div>

      <div className="composer">
        {cases.length > 0 && (
          <select className="input" style={{ marginBottom: 8, maxWidth: 520 }} value={attach} onChange={(e) => setAttach(e.target.value)}>
            <option value="">No analysis attached</option>
            {cases.map((c) => <option key={c.id} value={c.id}>Attach: {caseLabel(c)}</option>)}
          </select>
        )}
        <form onSubmit={(e) => { e.preventDefault(); send(text, attach || null); }}>
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Message MedVisionAI…" maxLength={6000} disabled={!!offline}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text, attach || null); } }} rows={1} />
          <button className="btn primary" disabled={busy || !text.trim() || !!offline}>Send</button>
        </form>
        <div className="foot">AI answers can be wrong; verify with a specialist. Do not enter names or other patient-identifying details.</div>
      </div>
    </>
  );
}
