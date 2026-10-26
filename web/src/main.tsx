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

/** Only the triage queue is restricted (coordinator codes); every other page is open and asks for a code on use. */
function CoordinatorOnly({ children }: { children: ReactNode }) {
  const { ready, licence } = useStore();
  if (!ready) return null;
  return licence?.role === "coordinator" ? <>{children}</> : <Navigate to="/appointments" replace />;
}

function App() {
  const location = useLocation();
  return (
    <Layout>
      <Routes location={location}>
        <Route path="/" element={<Platform />} />
        <Route path="/brain-mri" element={<BrainMRI />} />
        <Route path="/colorectal" element={<Colorectal />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/appointments" element={<Appointments />} />
        <Route path="/triage" element={<CoordinatorOnly><Triage /></CoordinatorOnly>} />
        <Route path="/benchmarks" element={<Benchmarks />} />
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
