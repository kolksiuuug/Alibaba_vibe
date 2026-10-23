import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Для локальной отладки: npm run dev проксирует /api на поднятый compose-стек.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8080" },
  },
});
