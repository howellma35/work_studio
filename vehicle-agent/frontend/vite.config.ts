import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  // 生产环境挂在 /vehicle/ 下（nginx location /vehicle/ 路由）
  // 开发环境用 / （直接访问 localhost:5174）
  base: mode === 'production' ? '/vehicle/' : '/',
  server: {
    port: 5174,
    host: true,
    proxy: {
      '/api/copilotkit': {
        target: 'http://localhost:4000',
        changeOrigin: true,
        ws: true,
      },
      '/api/vehicle': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
}));
