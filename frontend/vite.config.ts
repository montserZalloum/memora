import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/assets/memora/frontend/', // Hashed assets base URL
  build: {
    outDir: '../memora/public/frontend', // Build into Frappe public folder
    emptyOutDir: true,
    manifest: '.vite/manifest.json', // Manifest file for hashed asset tracking
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000', // Proxy API calls during development
    }
  }
})