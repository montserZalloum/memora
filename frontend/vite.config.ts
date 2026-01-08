import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Only use base path in production build, not in dev
  base: command === 'build' ? '/assets/memora/frontend/' : '/',
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
      '/api': {
        target: 'https://x.conanacademy.com',
        changeOrigin: true,
        secure: true,
        cookieDomainRewrite: 'localhost',
        // Forward credentials (cookies, auth headers)
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Ensure origin is set correctly
            proxyReq.setHeader('Origin', 'https://x.conanacademy.com');
          });
        },
      },
      // Also proxy the /assets path for static files from backend
      '/assets': {
        target: 'https://x.conanacademy.com',
        changeOrigin: true,
        secure: true,
      },
      // Proxy /files for uploaded files
      '/files': {
        target: 'https://x.conanacademy.com',
        changeOrigin: true,
        secure: true,
      }
    }
  }
}))