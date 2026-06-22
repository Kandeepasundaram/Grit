import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/v1': 'http://localhost:8000',
      '/oauth': 'http://localhost:8000',
      '/webhooks': 'http://localhost:8000',
    },
  },
})
