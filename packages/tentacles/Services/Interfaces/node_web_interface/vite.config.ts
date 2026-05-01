import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

export default defineConfig({
  base: "/app/",
  plugins: [tailwindcss(), tanstackRouter(), react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
})
