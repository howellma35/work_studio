/// <reference types="vite/client" />

// 博客文档虚拟模块（由 vite.config.ts 的 blogDocsPlugin 提供）
declare module 'virtual:blog-docs' {
  const docs: { dir: string; name: string; content: string }[];
  export default docs;
}
