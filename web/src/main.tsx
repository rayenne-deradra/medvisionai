import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import { StoreProvider, useStore } from "./store";
import Platform from "./pages/Platform";
import BrainMRI from "./pages/BrainMRI";
import Colorectal from "./pages/Colorectal";
import Assistant from "./pages/Assistant";
import Appointments from "./pages/Appointments";
import Triage from "./pages/Triage";
import Benchmarks from "./pages/Benchmarks";
import Activation from "./pages/Activation";
import "./styles.css";

/** Pages behind the activation code: signed-out visitors go to Activation and come back afterwards. */
function Gate({ children, coordinator }: { children: ReactNode; coordinator?: boolean }) {
  const { ready, signedIn, licence } = useStore();
  const location = useLocation();
  if (!ready) return null;
  if (!signedIn) return <Navigate to={`/activation?next=${encodeURIComponent(location.pathname)}`} replace />;
  if (coordinator && licence?.role !== "coordinator") return <Navigate to="/appointments" replace />;
  return <>{children}</>;
}

function App() {
  const location = useLocation();
  return (
    <Layout>
      <Routes location={location}>
        <Route path="/" element={<Platform />} />
        <Route path="/brain-mri" element={<Gate><BrainMRI /></Gate>} />
        <Route path="/colorectal" element={<Gate><Colorectal /></Gate>} />
        <Route path="/assistant" element={<Gate><Assistant /></Gate>} />
        <Route path="/appointments" element={<Gate><Appointments /></Gate>} />
        <Route path="/triage" element={<Gate coordinator><Triage /></Gate>} />
        <Route path="/benchmarks" element={<Gate><Benchmarks /></Gate>} />
        <Route path="/activation" element={<Activation />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <StoreProvider><App /></StoreProvider>
    </BrowserRouter>
  </StrictMode>,
);
