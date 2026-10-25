// App-wide state: server config, the signed-in licence, analysed cases and the assistant conversation.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
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
  cases: Case[];
  addCase: (c: Case) => void;
  messages: ChatMsg[];
  setMessages: (fn: (m: ChatMsg[]) => ChatMsg[]) => void;
  pendingCase: string | null;          // case to attach on the assistant page
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
    };
    window.addEventListener("mvai:unauthorized", onUnauthorized);
    return () => window.removeEventListener("mvai:unauthorized", onUnauthorized);
  }, []);

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

  const value = useMemo<Store>(() => ({
    config, licence, ready,
    signedIn: !!licence || (config ? !config.licensing : false),
    signIn, signOut,
    cases, addCase: (c) => setCases((prev) => [c, ...prev].slice(0, 30)),
    messages, setMessages: (fn) => setMessagesState(fn),
    pendingCase, setPendingCase,
  }), [config, licence, ready, signIn, signOut, cases, messages, pendingCase]);

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
