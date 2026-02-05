import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const apiPort = process.env.VITE_API_PORT || '8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: `http://localhost:${apiPort}`,
        changeOrigin: true,
      }
    }
  }
})
