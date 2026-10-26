import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { motion } from "framer-motion";
import { AlertTriangle, Bot, MessageSquareText, Paperclip, SendHorizontal, Sparkles } from "lucide-react";
import { api } from "../api";
import { caseLabel, useStore, type ChatMsg } from "../store";
import { PageHead, PulseLine } from "../components/ui";

const SUGGESTIONS = [
  "How do glioma, meningioma and pituitary tumours differ on brain MRI?",
  "What are the early warning signs of colorectal cancer?",
  "How should I read a Grad-CAM heatmap on a tissue patch?",
  "What does a U-Net lesion outline on an MRI slice tell me, and what not?",
];

export default function Assistant() {
  const { config, cases, messages, setMessages, pendingCase, setPendingCase, requireAuth } = useStore();
  const [text, setText] = useState("");
  const [attach, setAttach] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const autoSent = useRef(false);

  const send = (content: string, caseId: string | null) => {
    if (busy || !content.trim()) return;
    requireAuth(async () => {
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
    }, "The AI Assistant needs your organisation's activation code.");
  };

  useEffect(() => {
    if (pendingCase && !autoSent.current) {
      autoSent.current = true;
      setPendingCase(null);
      send("Please explain this MedVisionAI analysis.", pendingCase);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingCase]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages]);

  const offline = !!config && !config.ai;
  return (
    <>
      <PageHead icon={<MessageSquareText size={16} />} eyebrow="Medical and health questions only" title="AI Assistant">
        Ask about brain MRI, colorectal pathology or one of your analyses. It explains results and their uncertainty; it never gives a diagnosis.
      </PageHead>
      {offline && <div className="alert warning" style={{ marginBottom: 16 }}><AlertTriangle size={18} />The assistant is offline on this server: no AI key is configured. Image analysis still works.</div>}

      <div className="chat">
        {messages.length === 0 && (
          <div className="card empty" style={{ paddingBottom: 28 }}>
            <PulseLine />
            <div className="h3">What would you like to know?</div>
            <p>Pick a question to start, or attach one of your analyses below.</p>
            <div className="chips" style={{ justifyContent: "center", marginTop: 8 }}>
              {SUGGESTIONS.map((s) => <button key={s} className="chip-btn" onClick={() => send(s, null)} disabled={offline}><Sparkles size={15} />{s}</button>)}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <motion.div key={i} className={`msg ${m.role}${m.error ? " error" : ""}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
            {m.role === "assistant" && <div className="who"><Bot size={15} />MedVisionAI</div>}
            {m.caseLabel && <div className="att"><Paperclip size={13} />{m.caseLabel}</div>}
            {m.role === "assistant" && !m.content && busy && i === messages.length - 1
              ? <div className="typing" aria-label="Writing"><i /><i /><i /></div>
              : m.role === "assistant" ? <Markdown>{m.content}</Markdown> : <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>}
          </motion.div>
        ))}
        <div ref={bottom} />
      </div>

      <div className="composer">
        {cases.length > 0 && (
          <div className="row" style={{ marginBottom: 8 }}>
            <Paperclip size={16} className="muted" />
            <select className="input" style={{ maxWidth: 520, height: 36 }} value={attach} onChange={(e) => setAttach(e.target.value)} aria-label="Attach an analysis">
              <option value="">No analysis attached</option>
              {cases.map((c) => <option key={c.id} value={c.id}>Attach: {caseLabel(c)}</option>)}
            </select>
          </div>
        )}
        <form onSubmit={(e) => { e.preventDefault(); send(text, attach || null); }}>
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask a medical question…" maxLength={6000} disabled={offline} rows={1}
            aria-label="Message" onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text, attach || null); } }} />
          <button className="btn primary" disabled={busy || !text.trim() || offline} aria-label="Send"><SendHorizontal size={17} /></button>
        </form>
        <p className="hint">AI answers can be wrong; verify with a specialist. Don't enter names or other details that identify a patient.</p>
      </div>
    </>
  );
}
