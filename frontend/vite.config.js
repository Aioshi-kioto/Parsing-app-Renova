import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Get API port from environment (set by start.py) or default to 8000
// In dev mode, Vite reads from process.env, but we need to handle it properly
const apiPort = process.env.VITE_API_PORT || '8001'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: `http://localhost:${apiPort}`,
        changeOrigin: true,
        rewrite: (path) => path, // Don't rewrite, keep /api prefix
      }
    }
  }
})
