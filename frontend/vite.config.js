import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: '0.0.0.0',  // 允许外部 IP 访问
    port: 5174
  },
  plugins: [react(), tailwindcss()],
})
