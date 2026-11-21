import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// `npm run build` writes into ./dist, which the FastAPI backend serves at "/".
// `npm run dev` serves the UI on :5173 and proxies /api to uvicorn on :8000.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
