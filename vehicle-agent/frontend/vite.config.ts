import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    host: true,
    proxy: {
      '/agent': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        ws: true,
      },
      '/api/vehicle': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
});
