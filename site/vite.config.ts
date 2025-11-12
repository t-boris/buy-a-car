import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // GitHub Pages base path (adjust if your repo name is different)
  // For repo 'username.github.io', use '/'
  // For repo 'buing-a-car', use '/buing-a-car/'
  base: '/buing-a-car/',

  // Build output directory
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
  },

  // Public directory disabled - data files copied by workflow
  publicDir: false,

  // Dev server configuration
  server: {
    port: 3000,
    host: true,
  },
})
