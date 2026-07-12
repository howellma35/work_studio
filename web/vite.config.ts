import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * 博客文档加载插件
 *
 * 用 fs 直接读取 docs/ 和 vehicle-agent/docs/ 下的 .md 文件，
 * 通过虚拟模块 virtual:blog-docs 暴露给前端（blogs-loader.ts 消费）。
 *
 * 为什么不用 import.meta.glob：docs 目录在 Vite 项目根 (web/) 之外，
 * 且本地开发与 Docker 构建的目录层级不同
 *   - 本地：loader 在 web/src/data，项目根在 web/..（../../../ 才到）
 *   - Docker：web/ 被 COPY 扁平化进 /app，loader 在 /app/src/data，2 层就到 /app
 * 相对路径无法同时兼容两种布局，因此用「候选根目录 + 绝对路径」扫描，
 * 本地和 Docker 都能命中。
 */
function blogDocsPlugin() {
  const virtualId = 'virtual:blog-docs';
  const resolvedId = '\0' + virtualId;
  const subDirs = ['docs', 'vehicle-agent/docs'];

  return {
    name: 'blog-docs-loader',
    resolveId(id: string) {
      if (id === virtualId) return resolvedId;
    },
    load(id: string) {
      if (id !== resolvedId) return;
      // vite.config.ts 所在目录：本地为 web/，Docker 构建为 /app（web/ 被扁平化）
      const here = path.dirname(fileURLToPath(import.meta.url));
      // 候选根目录：项目根（本地 web/..）与 web 自身（Docker /app，docs 被复制到 /app 下）
      const roots = [path.resolve(here, '..'), here];
      const seen = new Set<string>();
      const docs: { dir: string; name: string; content: string }[] = [];
      for (const root of roots) {
        for (const sub of subDirs) {
          const dir = path.join(root, sub);
          if (!fs.existsSync(dir)) continue;
          for (const name of fs.readdirSync(dir)) {
            if (!name.endsWith('.md')) continue;
            const key = `${sub}/${name}`;
            if (seen.has(key)) continue;
            seen.add(key);
            docs.push({ dir: sub, name, content: fs.readFileSync(path.join(dir, name), 'utf-8') });
          }
        }
      }
      return `export default ${JSON.stringify(docs)};`;
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), blogDocsPlugin()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api/ai': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api/knowledge': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
