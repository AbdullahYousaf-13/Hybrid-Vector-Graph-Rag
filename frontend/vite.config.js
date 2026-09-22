import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Keeps the API same-origin in development too, so the app calls the same
    // relative /api path it will use in production.
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
