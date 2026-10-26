// App-wide state: server config, the signed-in licence, analysed cases, the assistant conversation,
// and the activation dialog (pages are open to everyone; actions that need a licence ask for the code first).
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, getToken, setToken, type Case, type Config, type Licence } from "./api";

export interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  caseLabel?: string;
  error?: boolean;
}

interface Store {
  config: Config | null;
  licence: Licence | null;
  ready: boolean;
  signedIn: boolean;
  signIn: (token: string, licence: Licence) => void;
  signOut: () => void;
  /** Runs `action` now if a licence is active, otherwise opens the activation dialog and runs it after activation. */
  requireAuth: (action?: () => void, reason?: string) => void;
  dialog: { open: boolean; reason: string };
  closeDialog: () => void;
  completeDialog: () => void;
  cases: Case[];
  addCase: (c: Case) => void;
  messages: ChatMsg[];
  setMessages: (fn: (m: ChatMsg[]) => ChatMsg[]) => void;
  pendingCase: string | null;
  setPendingCase: (id: string | null) => void;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<Config | null>(null);
  const [licence, setLicence] = useState<Licence | null>(null);
  const [ready, setReady] = useState(false);
  const [cases, setCases] = useState<Case[]>([]);
  const [messages, setMessagesState] = useState<ChatMsg[]>([]);
  const [pendingCase, setPendingCase] = useState<string | null>(null);
  const [dialog, setDialog] = useState({ open: false, reason: "" });
  const afterAuth = useRef<(() => void) | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setConfig(await api.get<Config>("/api/config"));
        if (getToken()) setLicence(await api.get<Licence>("/api/auth/me"));
      } catch {
        setToken(null);
      } finally {
        setReady(true);
      }
    })();
    const onUnauthorized = () => {
      setToken(null);
      setLicence(null);
      setDialog({ open: true, reason: "Your session has ended. Enter the activation code again to continue." });
    };
    window.addEventListener("mvai:unauthorized", onUnauthorized);
    return () => window.removeEventListener("mvai:unauthorized", onUnauthorized);
  }, []);

  const signedIn = !!licence || (config ? !config.licensing : false);

  const signIn = useCallback((token: string, lic: Licence) => {
    setToken(token);
    setLicence((prev) => {
      if (prev && prev.licence_id !== lic.licence_id) {
        setCases([]);
        setMessagesState([]);
      }
      return lic;
    });
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setLicence(null);
    setCases([]);
    setMessagesState([]);
  }, []);

  const requireAuth = useCallback((action?: () => void, reason = "") => {
    if (signedIn) {
      action?.();
      return;
    }
    afterAuth.current = action || null;
    setDialog({ open: true, reason });
  }, [signedIn]);

  const value = useMemo<Store>(() => ({
    config, licence, ready, signedIn, signIn, signOut, requireAuth, dialog,
    closeDialog: () => { afterAuth.current = null; setDialog({ open: false, reason: "" }); },
    completeDialog: () => {
      setDialog({ open: false, reason: "" });
      const next = afterAuth.current;
      afterAuth.current = null;
      if (next) setTimeout(next, 0);    // after the new token is stored
    },
    cases, addCase: (c) => setCases((prev) => [c, ...prev].slice(0, 30)),
    messages, setMessages: (fn) => setMessagesState(fn),
    pendingCase, setPendingCase,
  }), [config, licence, ready, signedIn, signIn, signOut, requireAuth, dialog, cases, messages, pendingCase]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore(): Store {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore outside StoreProvider");
  return s;
}

export function caseLabel(c: Case): string {
  return `${c.modality === "brain_mri" ? "Brain MRI" : "Tissue"} · ${c.report.filename} · ${c.report.finding}`;
}
