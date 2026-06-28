import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    // Stuur API- en videostreams door naar de Flask-server tijdens 'npm run dev'.
    // Zo zie je de echte camerabeelden op http://localhost:5173 zolang run.py draait.
    proxy: {
      '/api': 'http://localhost:5001',
      '/video_feed_ocr': 'http://localhost:5001',
      '/video_feed_cam': 'http://localhost:5001',
    },
  },
})
