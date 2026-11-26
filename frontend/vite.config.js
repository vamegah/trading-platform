import react from "@vitejs/plugin-react";
import { defineConfig, transformWithOxc } from "vite";

// Source files under src/ use the .js extension for JSX. Vite 8 transforms with
// Oxc (esbuild is gone), so parse those files as JSX before the React plugin.
const jsAsJsx = {
  name: "js-as-jsx",
  enforce: "pre",
  async transform(code, id) {
    if (!/[\\/]src[\\/].*\.js$/.test(id)) return null;
    return transformWithOxc(code, id, {
      lang: "jsx",
      jsx: { runtime: "automatic" },
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
  plugins: [jsAsJsx, react()],
});
