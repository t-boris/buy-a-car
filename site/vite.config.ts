import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // GitHub Pages base path (adjust if your repo name is different)
  // For repo 'username.github.io', use '/'
  // For repo 'buy-a-car', use '/buy-a-car/'
  base: '/buy-a-car/',

  // Build output directory
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
  },

  // Public directory for dev - data files served from here
  publicDir: 'public',

  // Dev server configuration
  server: {
    port: 3000,
    host: true,
  },
})
