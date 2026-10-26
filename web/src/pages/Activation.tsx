import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Brain, KeyRound, LogOut, MessageSquareText, Microscope, ShieldCheck } from "lucide-react";
import { useStore } from "../store";
import { ActivationForm } from "../components/ActivationForm";
import { PageHead } from "../components/ui";

export default function Activation() {
  const { config, licence, signOut } = useStore();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [switching, setSwitching] = useState(false);

  return (
    <>
      <PageHead icon={<KeyRound size={16} />} eyebrow="Account" title="Activation">
        Pages are open to explore. Running analyses, the AI Assistant and referrals need the activation code your organisation received.
      </PageHead>
      <div className="grid-2" style={{ alignItems: "start" }}>
        <div className="card pad-lg">
          {licence ? (
            <>
              <div className="row" style={{ marginBottom: 14 }}><span className="badge success"><ShieldCheck size={14} />Licence active</span></div>
              <h2 className="h2">{licence.organisation}</h2>
              <dl className="kv" style={{ marginTop: 16 }}>
                <div><dt>Plan</dt><dd>{licence.plan || "—"}</dd></div>
                <div><dt>Valid until</dt><dd>{licence.expires || "No expiry"}</dd></div>
                <div><dt>Access</dt><dd>{licence.role === "coordinator" ? "Hospital coordinator" : "Clinical user"}</dd></div>
              </dl>
              <hr className="divider" />
              {switching ? <ActivationForm onDone={() => setSwitching(false)} autoFocus /> : (
                <div className="row"><button className="btn" onClick={() => setSwitching(true)}><KeyRound size={16} />Use a different code</button>
                  <button className="btn quiet" onClick={signOut}><LogOut size={16} />Sign out</button></div>)}
            </>
          ) : config && !config.licensing ? (
            <><h2 className="h2">Demo mode</h2><p className="muted">Licensing is switched off on this server, so every feature works without a code.</p></>
          ) : (
            <><h2 className="h2" style={{ marginBottom: 6 }}>Enter your code</h2>
              <p className="muted small" style={{ marginTop: 0, marginBottom: 18 }}>It looks like MVAI-XXXX-XXXX-XXXX-XXXX and is linked to your organisation.</p>
              <ActivationForm autoFocus onDone={() => navigate(params.get("next") || "/brain-mri")} /></>
          )}
        </div>
        <div className="card pad-lg">
          <h3 className="h3" style={{ marginBottom: 14 }}>What the code unlocks</h3>
          <ul className="checks">
            <li><Brain size={16} />Brain tumour MRI analysis: CNN ensemble, lesion outline and triage score</li>
            <li><Microscope size={16} />Colorectal tissue analysis with Grad-CAM and tile scanning</li>
            <li><MessageSquareText size={16} />The AI Assistant, with your analyses attached</li>
            <li><ShieldCheck size={16} />Specialist referrals, and the triage queue for coordinator codes</li>
          </ul>
          <hr className="divider" />
          <p className="small muted" style={{ margin: 0 }}>Codes are issued to hospitals, laboratories and research groups once their subscription is confirmed. Each code has an
            expiry date, and your browser remembers it for 30 days.</p>
        </div>
      </div>
    </>
  );
}
