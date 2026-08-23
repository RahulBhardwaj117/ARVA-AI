import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      "next/link": path.resolve(
        __dirname,
        "node_modules/vinext/dist/shims/link.js",
      ),
      "next/navigation": path.resolve(
        __dirname,
        "node_modules/vinext/dist/shims/navigation.js",
      ),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
