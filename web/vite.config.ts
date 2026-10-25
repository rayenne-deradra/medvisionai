import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the FastAPI server runs on :8000; Vite forwards API and static requests to it.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000", "/static": "http://localhost:8000" },
  },
  build: { outDir: "dist", chunkSizeWarningLimit: 900 },
});
