import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  // Relative, so the build works both at a domain root and under a subpath.
  base: "./",
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      // Two entry points. `index.html` is the landing page a visitor lands
      // on; the IDE is a separate document at /app.html, so the heavy
      // bundle is not downloaded by someone who only wants to read about
      // the tool.
      input: {
        main: resolve(__dirname, "index.html"),
        app: resolve(__dirname, "app.html"),
      },
    },
  },
});
