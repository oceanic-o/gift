import { defineConfig, splitVendorChunkPlugin } from "vite";
import { fileURLToPath } from "url";
import path from "path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";

const srcPath = fileURLToPath(new URL("./src", import.meta.url));

export default defineConfig({
  plugins: [
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
    // Split common vendor code automatically
    splitVendorChunkPlugin(),
  ],
  resolve: {
    alias: {
      // Alias @ to the src directory
      "@": srcPath,
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ["**/*.svg", "**/*.csv"],

  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes("node_modules")) {
            // Keep a single vendor chunk that includes React to avoid circular graphs
            if (id.includes("motion")) return "motion";
            if (id.includes("lucide")) return "icons";
            return "vendor";
          }
        },
      },
    },
    // Keep warnings reasonable; real fixes come from lazy-route splitting which we already added
    chunkSizeWarningLimit: 900,
  },
});
