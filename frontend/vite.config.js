import react from "@vitejs/plugin-react";
import { defineConfig, transformWithEsbuild } from "vite";

const jsAsJsx = {
  name: "js-as-jsx",
  async transform(code, id) {
    if (!/src[\\/].*\.js$/.test(id)) return null;
    return transformWithEsbuild(code, id, {
      loader: "jsx",
      jsx: "automatic",
    });
  },
};

export default defineConfig({
  cacheDir: "../.vite-cache/frontend",
  resolve: {
    alias: {
      "@tradingview/lightweight-charts": "lightweight-charts",
    },
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        ".js": "jsx",
      },
    },
  },
  plugins: [jsAsJsx, react()],
});
