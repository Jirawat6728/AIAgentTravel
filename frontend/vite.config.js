import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react({
    fastRefresh: true
  })],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  optimizeDeps: {
    include: ['react', 'react-dom']
  }
})
